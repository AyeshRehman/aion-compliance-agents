# src/copilots/compliance/kyc_validation/agno_kyc_agent.py
"""
KYC Validation Agent for SAMA Compliance
Validates customer documents against SAMA KYC requirements
"""

import os
import sys
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Agno framework
from agno.agent import Agent

# Import shared components
from shared.ollama_agno import OllamaForAgno
from shared.kafka_handler import KafkaHandler
from shared.models import KYCValidation, Document, get_database_session, create_tables

# Import ChromaDB for document retrieval
import chromadb

# Import Redis for caching
import redis

# Logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SAMAKYCValidationAgent(Agent):
    """
    KYC Validation Agent
    
    This agent:
    1. Receives document IDs from Kafka events
    2. Retrieves documents from database/ChromaDB
    3. Validates against SAMA KYC requirements
    4. Stores validation results
    5. Sends events for next steps
    """
    
    def __init__(self):
        """Initialize KYC Validation Agent"""
        
        print("Starting KYC Validation Agent...")
        
        # Initialize Ollama LLM
        try:
            self.llm = OllamaForAgno(
                model="mistral",  # or your model
                base_url="http://localhost:11434"
            )
        except Exception as e:
            print(f"Warning: Ollama not initialized: {e}")
            self.llm = None
        
        # Initialize ChromaDB for document retrieval
        os.makedirs("./data/chroma_db", exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path="./data/chroma_db")
        self.collection = self.chroma_client.get_or_create_collection(
            name="sama_documents"
        )
        
        # Initialize Redis for caching
        try:
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                decode_responses=True
            )
            self.redis_client.ping()
            print("Redis cache connected")
        except:
            self.redis_client = None
            print("Redis not available")
        
        # Initialize base Agent
        super().__init__(
            name="KYCValidationAgent",
            model=self.llm,
            description="Validates documents for SAMA KYC compliance"
        )
        
        # Initialize Kafka
        self.kafka_handler = KafkaHandler()
        
        # Initialize database
        self.db_session = None
        try:
            create_tables()
            self.db_session = get_database_session()
            print("Database connected")
        except:
            print("Database not available")
            self.memory_storage = {}
        
        print("KYC Validation Agent ready!")
    
    def validate_kyc(self, document_id: str, customer_id: str) -> Dict[str, Any]:
        """
        Main KYC validation function
        
        Args:
            document_id: ID of document to validate
            customer_id: Customer ID
            
        Returns:
            Validation results dictionary
        """
        
        print(f"Validating KYC for document: {document_id}")
        
        # Check cache first
        if self.redis_client:
            cached = self._get_from_cache(f"kyc:{document_id}")
            if cached:
                print("Returning cached KYC validation")
                return cached
        
        # Retrieve document from database
        document = self._retrieve_document(document_id)
        if not document:
            return {
                "status": "error",
                "message": "Document not found"
            }
        
        # Perform KYC validation
        validation_result = self._perform_validation(document, customer_id)
        
        # Store results
        self._store_validation(validation_result)
        
        # Cache results
        if self.redis_client:
            self._save_to_cache(f"kyc:{document_id}", validation_result)
        
        # Send events
        self._send_events(validation_result)
        
        print(f"KYC validation complete: {validation_result['validation_status']}")
        return validation_result
    
    def _retrieve_document(self, document_id: str) -> Dict:
        """Retrieve document from database or ChromaDB"""
        
        # Try database first
        if self.db_session:
            try:
                doc = self.db_session.query(Document).filter_by(
                    id=document_id
                ).first()
                
                if doc:
                    return {
                        "id": doc.id,
                        "text": doc.extracted_text,
                        "type": doc.document_type,
                        "customer_id": doc.customer_id
                    }
            except Exception as e:
                logger.error(f"Database retrieval error: {e}")
        
        # Try ChromaDB
        try:
            results = self.collection.get(
                ids=[document_id]
            )
            
            if results['documents']:
                return {
                    "id": document_id,
                    "text": results['documents'][0],
                    "type": results['metadatas'][0].get('document_type', 'unknown'),
                    "customer_id": results['metadatas'][0].get('customer_id')
                }
        except Exception as e:
            logger.error(f"ChromaDB retrieval error: {e}")
        
        return None
    
    def _perform_validation(self, document: Dict, customer_id: str) -> Dict:
        """
        Perform KYC validation on document
        
        Args:
            document: Document data
            customer_id: Customer ID
            
        Returns:
            Validation results
        """
        
        validation_id = hashlib.md5(
            f"{document['id']}_{datetime.now()}".encode()
        ).hexdigest()
        
        # Get document type and text
        doc_type = document.get('type', 'unknown')
        doc_text = document.get('text', '')
        
        # Perform validation based on document type
        if doc_type == 'commercial_registration':
            validation = self._validate_commercial_registration(doc_text)
        elif doc_type == 'national_id':
            validation = self._validate_national_id(doc_text)
        elif doc_type == 'bank_statement':
            validation = self._validate_bank_statement(doc_text)
        else:
            validation = self._validate_generic(doc_text)
        
        # Use Ollama for enhanced validation if available
        if self.llm:
            ai_validation = self._ai_validate(doc_text, doc_type)
            validation.update(ai_validation)
        
        # Prepare result
        result = {
            "validation_id": validation_id,
            "document_id": document['id'],
            "customer_id": customer_id,
            "document_type": doc_type,
            "validation_status": validation.get('status', 'pending'),
            "validation_score": validation.get('score', 0.0),
            "identity_verified": validation.get('identity_verified', False),
            "address_verified": validation.get('address_verified', False),
            "business_verified": validation.get('business_verified', False),
            "issues": validation.get('issues', []),
            "recommendations": validation.get('recommendations', []),
            "validated_at": datetime.now().isoformat()
        }
        
        return result
    
    def _validate_commercial_registration(self, text: str) -> Dict:
        """Validate commercial registration document"""
        
        import re
        
        issues = []
        score = 0.0
        
        # Check for CR number (10 digits)
        if re.search(r'\b\d{10}\b', text):
            score += 0.3
        else:
            issues.append("Valid 10-digit CR number not found")
        
        # Check for company name
        if any(word in text.lower() for word in ['company', 'corporation', 'شركة']):
            score += 0.2
        else:
            issues.append("Company name not clearly identified")
        
        # Check for capital amount
        if 'capital' in text.lower() or 'رأس المال' in text:
            score += 0.2
        else:
            issues.append("Capital amount not specified")
        
        # Check for SAR currency
        if 'sar' in text.lower() or 'ريال' in text:
            score += 0.2
        else:
            issues.append("Saudi currency not mentioned")
        
        # Check for dates
        if re.search(r'\d{1,2}/\d{1,2}/\d{4}', text):
            score += 0.1
        
        return {
            "status": "passed" if score >= 0.7 else "failed",
            "score": score,
            "business_verified": score >= 0.7,
            "issues": issues,
            "recommendations": ["Ensure all CR details are visible"] if issues else []
        }
    
    def _validate_national_id(self, text: str) -> Dict:
        """Validate national ID document"""
        
        import re
        
        issues = []
        score = 0.0
        
        # Check for Saudi ID number (10 digits starting with 1 or 2)
        if re.search(r'\b[12]\d{9}\b', text):
            score += 0.4
        else:
            issues.append("Valid Saudi ID number not found")
        
        # Check for name
        if any(word in text.lower() for word in ['name', 'الاسم']):
            score += 0.3
        
        # Check for date of birth
        if any(word in text.lower() for word in ['birth', 'الميلاد']):
            score += 0.2
        
        # Check for nationality
        if any(word in text.lower() for word in ['saudi', 'سعودي']):
            score += 0.1
        
        return {
            "status": "passed" if score >= 0.7 else "failed",
            "score": score,
            "identity_verified": score >= 0.7,
            "issues": issues,
            "recommendations": ["Ensure ID is clearly readable"] if issues else []
        }
    
    def _validate_bank_statement(self, text: str) -> Dict:
        """Validate bank statement"""
        
        import re
        
        issues = []
        score = 0.0
        
        # Check for account number
        if re.search(r'\b\d{10,}\b', text):
            score += 0.3
        else:
            issues.append("Account number not found")
        
        # Check for IBAN
        if re.search(r'\bSA\d{22}\b', text):
            score += 0.3
        else:
            issues.append("Saudi IBAN not found")
        
        # Check for SAR currency
        if 'sar' in text.lower() or 'ريال' in text:
            score += 0.2
        else:
            issues.append("SAR currency not mentioned")
        
        # Check for bank name
        if any(word in text.lower() for word in ['bank', 'بنك']):
            score += 0.2
        
        return {
            "status": "passed" if score >= 0.6 else "failed",
            "score": score,
            "address_verified": score >= 0.6,
            "issues": issues,
            "recommendations": ["Provide recent bank statement"] if issues else []
        }
    
    def _validate_generic(self, text: str) -> Dict:
        """Generic validation for unknown document types"""
        
        return {
            "status": "pending",
            "score": 0.5,
            "issues": ["Document type not recognized"],
            "recommendations": ["Manual review required"]
        }
    
    def _ai_validate(self, text: str, doc_type: str) -> Dict:
        """Use Ollama for AI-powered validation"""
        
        prompt = f"""
        Validate this {doc_type} document for SAMA KYC compliance.
        
        Document content: {text[:1000]}
        
        Check for:
        1. Required information completeness
        2. SAMA compliance
        3. Document authenticity indicators
        
        Return JSON with:
        - validation_passed (true/false)
        - confidence_score (0-1)
        - missing_items (list)
        - compliance_notes (string)
        """
        
        try:
            response = self.llm.run(prompt)
            
            # Parse JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start != -1 and end > 0:
                json_str = response[start:end]
                ai_result = json.loads(json_str)
                
                return {
                    "ai_validated": True,
                    "ai_confidence": ai_result.get('confidence_score', 0.5),
                    "issues": ai_result.get('missing_items', []),
                    "ai_notes": ai_result.get('compliance_notes', '')
                }
        except Exception as e:
            logger.error(f"AI validation error: {e}")
        
        return {"ai_validated": False}
    
    def _store_validation(self, validation: Dict):
        """Store validation results in database"""
        
        if self.db_session:
            try:
                kyc_record = KYCValidation(
                    id=validation['validation_id'],
                    document_id=validation['document_id'],
                    customer_id=validation['customer_id'],
                    validation_status=validation['validation_status'],
                    validation_score=validation['validation_score'],
                    identity_verified=validation['identity_verified'],
                    address_verified=validation['address_verified'],
                    business_verified=validation['business_verified'],
                    validation_details=json.dumps({
                        "issues": validation['issues'],
                        "recommendations": validation['recommendations']
                    })
                )
                
                self.db_session.add(kyc_record)
                self.db_session.commit()
                print("Validation stored in database")
                
            except Exception as e:
                logger.error(f"Database storage error: {e}")
                self.db_session.rollback()
        else:
            # Store in memory
            if hasattr(self, 'memory_storage'):
                self.memory_storage[validation['validation_id']] = validation
    
    def _send_events(self, validation: Dict):
        """Send Kafka events"""
        
        # Send validation completed event
        self.kafka_handler.send_event(
            topic="kyc-validation-completed",
            key=validation['document_id'],
            value={
                "validation_id": validation['validation_id'],
                "document_id": validation['document_id'],
                "customer_id": validation['customer_id'],
                "status": validation['validation_status'],
                "score": validation['validation_score'],
                "validated_at": validation['validated_at']
            }
        )
        
        # Request compliance summary if validation passed
        if validation['validation_status'] == 'passed':
            self.kafka_handler.send_event(
                topic="compliance-summary-requested",
                key=validation['customer_id'],
                value={
                    "customer_id": validation['customer_id'],
                    "validation_id": validation['validation_id'],
                    "requested_at": datetime.now().isoformat()
                }
            )
    
    def _get_from_cache(self, key: str) -> Dict:
        """Get from Redis cache"""
        if self.redis_client:
            try:
                cached = self.redis_client.get(key)
                if cached:
                    return json.loads(cached)
            except:
                pass
        return None
    
    def _save_to_cache(self, key: str, data: Dict):
        """Save to Redis cache"""
        if self.redis_client:
            try:
                self.redis_client.setex(
                    key,
                    3600,  # 1 hour TTL
                    json.dumps(data)
                )
            except:
                pass


def test_kyc_agent():
    """Test the KYC Validation Agent"""
    
    print("\n" + "="*60)
    print("TESTING KYC VALIDATION AGENT")
    print("="*60)
    
    # Create agent
    agent = SAMAKYCValidationAgent()
    
    # First, create a document using Document Ingestion Agent
    from document_ingestion.agno_document_agent_ollama import SAMADocumentIngestionAgent
    
    doc_agent = SAMADocumentIngestionAgent()
    
    # Create test document
    test_file = "test_cr_for_kyc.txt"
    with open(test_file, 'w') as f:
        f.write("""
        Commercial Registration Certificate
        
        Company Name: Al-Rashid Technologies LLC
        Registration Number: 1010345678
        Issue Date: 01/01/2024
        Expiry Date: 31/12/2024
        
        Business Activities: Information Technology Services
        Authorized Capital: 5,000,000 SAR
        Paid Capital: 5,000,000 SAR
        
        Registered with Ministry of Commerce
        Kingdom of Saudi Arabia
        """)
    
    # Process document
    doc_result = doc_agent.process_document(test_file, "KYC_TEST_001")
    doc_id = doc_result['document_id']
    
    print(f"\nDocument created: {doc_id[:16]}...")
    
    # Now validate with KYC agent
    print("\nValidating KYC...")
    kyc_result = agent.validate_kyc(doc_id, "KYC_TEST_001")
    
    # Display results
    print("\n" + "-"*60)
    print("KYC VALIDATION RESULTS:")
    print("-"*60)
    print(f"Validation ID: {kyc_result.get('validation_id', 'N/A')[:16]}...")
    print(f"Status: {kyc_result.get('validation_status')}")
    print(f"Score: {kyc_result.get('validation_score', 0):.2f}")
    print(f"Business Verified: {kyc_result.get('business_verified')}")
    print(f"Identity Verified: {kyc_result.get('identity_verified')}")
    print(f"Address Verified: {kyc_result.get('address_verified')}")
    
    if kyc_result.get('issues'):
        print("\nIssues:")
        for issue in kyc_result['issues']:
            print(f"  - {issue}")
    
    if kyc_result.get('recommendations'):
        print("\nRecommendations:")
        for rec in kyc_result['recommendations']:
            print(f"  - {rec}")
    
    print("\n✅ KYC Validation Agent test complete!")


if __name__ == "__main__":
    test_kyc_agent()