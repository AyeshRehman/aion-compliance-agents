# src/copilots/compliance/document_ingestion/agno_document_agent_ollama.py
"""
Document Ingestion Agent - Simple version with Ollama
This agent processes documents for SAMA compliance using local LLM
"""

# Import required libraries
import hashlib  # To create unique document IDs
import os  # To work with files and paths
from datetime import datetime  # To add timestamps
from typing import Dict, Any  # For type hints
import json  # To handle JSON data
import logging  # To log errors and info

# Import PDF reader
import PyPDF2

# Import vector database
import chromadb

# Import Redis for caching
import redis

# Import Agno framework
from agno.agent import Agent

# Import our Ollama wrapper
from ..shared.ollama_agno import OllamaForAgno

# Import shared components
from ..shared.kafka_handler import KafkaHandler
from ..shared.models import Document, get_database_session, create_tables
from ..agno_config import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SAMADocumentIngestionAgent(Agent):
    """
    Main agent class for document processing
    Handles document ingestion and analysis for SAMA compliance
    """
    
    def __init__(self):
        """
        Initialize the agent with all required components
        """
        
        print("Starting Document Ingestion Agent...")
        
        # Initialize Ollama LLM (Local AI model)
        # This replaces Groq API with local Ollama
        try:
            self.llm = OllamaForAgno(
                model="mistral",  # Change this to your Ollama model name
                base_url="http://localhost:11434"  # Ollama server address
            )
        except Exception as e:
            print(f"Warning: Could not initialize Ollama: {e}")
            self.llm = None
        
        # Initialize ChromaDB (Local vector database)
        # This replaces Pinecone with free local alternative
        # Create data folder if it doesn't exist
        os.makedirs("./data/chroma_db", exist_ok=True)
        
        # Create ChromaDB client
        self.chroma_client = chromadb.PersistentClient(path="./data/chroma_db")
        
        # Create or get document collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="sama_documents"
        )
        
        # Initialize Redis for caching (optional)
        # This speeds up repeated document processing
        try:
            # Try to connect to Redis
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            print("Redis cache connected")
        except:
            # If Redis is not available, continue without it
            self.redis_client = None
            print("Redis not available, continuing without cache")
        
        # Initialize base Agent class from Agno
        super().__init__(
            name="DocumentIngestionAgent",
            model=self.llm,
            description="Processes documents for SAMA compliance"
        )
        
        # Initialize Kafka for event streaming
        self.kafka_handler = KafkaHandler()
        
        # Initialize database session
        self.db_session = None
        try:
            # Try to connect to database
            create_tables()
            self.db_session = get_database_session()
            print("Database connected")
        except:
            # If database is not available, use memory storage
            print("Database not available, using memory storage")
            self.memory_storage = {}
        
        print("Agent ready!")
    
    def process_document(self, file_path, customer_id=None):
        """
        Main function to process a document
        
        Args:
            file_path: Path to the document file
            customer_id: ID of the customer (optional)
            
        Returns:
            Dictionary with processing results
        """
        
        # Use ASCII-safe printing for filename
        try:
            print(f"Processing: {file_path}")
        except:
            print(f"Processing: {file_path.encode('ascii', 'ignore').decode('ascii')}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            return {"status": "error", "message": "File not found"}
        
        # Generate unique document ID
        doc_id = self._generate_id(file_path, customer_id)
        
        # Check cache first (if Redis is available)
        if self.redis_client:
            # Try to get from cache
            cached = self._get_from_cache(doc_id)
            if cached:
                print("Found in cache")
                return cached
        
        # Extract text from document
        text = self._extract_text(file_path)
        
        # Analyze document with Ollama
        analysis = self._analyze_with_ollama(text, file_path)
        
        # Create result dictionary
        result = {
            "document_id": doc_id,
            "filename": os.path.basename(file_path),
            "customer_id": customer_id,
            "extracted_text": text,
            "text_length": len(text),
            "document_type": analysis.get("document_type", "unknown"),
            "confidence": analysis.get("confidence", 0),
            "sama_compliant": analysis.get("sama_compliant", False),
            "issues": analysis.get("issues", []),
            "recommendations": analysis.get("recommendations", []),
            "processed_at": datetime.now().isoformat(),
            "status": "success"
        }
        
        # Store in vector database
        self._store_in_chromadb(doc_id, text, result)
        
        # Store in cache (if Redis is available)
        if self.redis_client:
            self._save_to_cache(doc_id, result)
        
        # Store in database or memory
        self._store_result(doc_id, result)
        
        # Send Kafka event
        self._send_event(result)
        
        print(f"Processing complete: {doc_id}")
        return result
    
    def _generate_id(self, file_path, customer_id):
        """
        Generate unique ID for document
        
        Args:
            file_path: Path to file
            customer_id: Customer ID
            
        Returns:
            Unique hash ID as string
        """
        # Combine file path, customer ID and timestamp
        unique_string = f"{file_path}_{customer_id}_{datetime.now()}"
        # Create MD5 hash
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    def _extract_text(self, file_path):
        """
        Extract text from document file
        
        Args:
            file_path: Path to document
            
        Returns:
            Extracted text as string
        """
        # Get file extension
        extension = os.path.splitext(file_path)[1].lower()
        
        # Handle PDF files
        if extension == '.pdf':
            try:
                # Open PDF file
                with open(file_path, 'rb') as file:
                    # Create PDF reader
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    # Extract text from each page
                    for page in pdf_reader.pages:
                        text += page.extract_text()
                    return text
            except Exception as e:
                return f"Error reading PDF: {e}"
        
        # Handle text files
        elif extension in ['.txt', '.text']:
            try:
                # Read text file
                with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                    return file.read()
            except Exception as e:
                return f"Error reading text file: {e}"
        
        # Unsupported file type
        else:
            return f"Unsupported file type: {extension}"
    
    def _analyze_with_ollama(self, text, file_path):
        """
        Analyze document using Ollama LLM
        
        Args:
            text: Document text
            file_path: Path to file
            
        Returns:
            Dictionary with analysis results
        """
        # Create prompt for Ollama
        prompt = f"""
        Analyze this document for SAMA compliance.
        
        Document: {text[:1000]}
        
        Return JSON with:
        - document_type (commercial_registration, national_id, bank_statement, tax_certificate, unknown)
        - confidence (0 to 1)
        - sama_compliant (true or false)
        - issues (list of problems)
        - recommendations (list of suggestions)
        """
        
        try:
            # Get response from Ollama
            response = self.llm.run(prompt)
            
            # Parse JSON from response
            # Find JSON in response
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start != -1 and end > 0:
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                # Return default if no JSON found
                return self._default_analysis()
                
        except Exception as e:
            print(f"Ollama error: {e}")
            # Return default analysis if Ollama fails
            return self._default_analysis()
    
    def _default_analysis(self):
        """
        Default analysis when AI is not available
        
        Returns:
            Dictionary with default values
        """
        return {
            "document_type": "unknown",
            "confidence": 0.5,
            "sama_compliant": False,
            "issues": ["Could not analyze document"],
            "recommendations": ["Please review manually"]
        }
    
    def _store_in_chromadb(self, doc_id, text, metadata):
        """
        Store document in ChromaDB vector database
        
        Args:
            doc_id: Document ID
            text: Document text
            metadata: Document metadata
        """
        try:
            # Store in ChromaDB
            self.collection.add(
                documents=[text[:1000]],  # Store first 1000 chars
                ids=[doc_id],
                metadatas=[{
                    "filename": metadata["filename"],
                    "customer_id": metadata["customer_id"],
                    "document_type": metadata["document_type"],
                    "processed_at": metadata["processed_at"]
                }]
            )
            print("Stored in ChromaDB")
        except Exception as e:
            print(f"ChromaDB error: {e}")
    
    def _get_from_cache(self, doc_id):
        """
        Get document from Redis cache
        
        Args:
            doc_id: Document ID
            
        Returns:
            Cached data or None
        """
        try:
            # Get from Redis
            cached = self.redis_client.get(f"doc:{doc_id}")
            if cached:
                # Convert JSON string to dictionary
                return json.loads(cached)
        except:
            pass
        return None
    
    def _save_to_cache(self, doc_id, data):
        """
        Save document to Redis cache
        
        Args:
            doc_id: Document ID
            data: Data to cache
        """
        try:
            # Convert to JSON and save in Redis
            # Expires after 1 hour (3600 seconds)
            self.redis_client.setex(
                f"doc:{doc_id}",
                3600,
                json.dumps(data)
            )
            print("Saved to cache")
        except:
            pass
    
    def _store_result(self, doc_id, result):
        """
        Store result in database or memory
        
        Args:
            doc_id: Document ID
            result: Processing result
        """
        if self.db_session:
            try:
                # Create database record
                document = Document(
                    id=doc_id,
                    filename=result['filename'],
                    customer_id=result['customer_id'],
                    extracted_text=result['extracted_text'],
                    processed=True
                )
                # Save to database
                self.db_session.add(document)
                self.db_session.commit()
                print("Stored in database")
            except Exception as e:
                print(f"Database error: {e}")
        else:
            # Store in memory if no database
            self.memory_storage[doc_id] = result
            print("Stored in memory")
    
    def _send_event(self, result):
        """
        Send event to Kafka
        
        Args:
            result: Processing result
        """
        try:
            # Send document processed event
            self.kafka_handler.send_event(
                topic="document-processed",
                key=result["document_id"],
                value={
                    "document_id": result["document_id"],
                    "customer_id": result["customer_id"],
                    "document_type": result["document_type"],
                    "sama_compliant": result["sama_compliant"],
                    "processed_at": result["processed_at"]
                }
            )
            
            # Send KYC validation request
            self.kafka_handler.send_event(
                topic="kyc-validation-requested",
                key=result["document_id"],
                value={
                    "document_id": result["document_id"],
                    "customer_id": result["customer_id"],
                    "document_type": result["document_type"]
                }
            )
            
            print("Events sent to Kafka")
        except Exception as e:
            print(f"Kafka error: {e}")


# Test function
def test_agent():
    """
    Test the document ingestion agent
    """
    print("\n" + "="*50)
    print("Testing Document Ingestion Agent")
    print("="*50)
    
    # Create agent
    agent = SAMADocumentIngestionAgent()
    
    # Create test file
    test_dir = "test_files"
    os.makedirs(test_dir, exist_ok=True)
    
    test_file = os.path.join(test_dir, "test_document.txt")
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write("""
        Commercial Registration Certificate
        Company: Test Company
        Registration Number: 1234567890
        Date: 2024-01-01
        This is a test document for SAMA compliance.
        """)
    
    # Process test document
    result = agent.process_document(test_file, "CUSTOMER_001")
    
    # Print results
    print("\nResults:")
    print(f"  Status: {result.get('status')}")
    print(f"  Document ID: {result.get('document_id')}")
    print(f"  Document Type: {result.get('document_type')}")
    print(f"  SAMA Compliant: {result.get('sama_compliant')}")
    print(f"  Issues: {result.get('issues')}")
    
    print("\nTest complete!")


if __name__ == "__main__":
    test_agent()