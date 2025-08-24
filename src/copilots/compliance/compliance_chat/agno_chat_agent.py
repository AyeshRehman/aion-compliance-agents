# src/copilots/compliance/compliance_chat/agno_chat_agent.py
"""
Compliance Chat Agent for SAMA Compliance
Interactive Q&A agent with RAG (Retrieval Augmented Generation)
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Agno framework
from agno.agent import Agent

# Import shared components
from shared.ollama_agno import OllamaForAgno
from shared.kafka_handler import KafkaHandler
from shared.models import get_database_session, Document, ComplianceSummary

# Import ChromaDB for RAG
import chromadb

# Import Redis for conversation history
import redis

# Logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SAMAComplianceChatAgent(Agent):
    """
    Compliance Chat Agent with RAG
    
    This agent:
    1. Answers questions about compliance
    2. Uses RAG to retrieve relevant documents
    3. Provides context-aware responses
    4. Maintains conversation history
    5. Gives compliance guidance
    """
    
    def __init__(self):
        """Initialize Compliance Chat Agent"""
        
        print("Starting Compliance Chat Agent...")
        
        # Initialize Ollama LLM
        try:
            self.llm = OllamaForAgno(
                model="mistral",
                base_url="http://localhost:11434"
            )
        except Exception as e:
            print(f"Warning: Ollama not initialized: {e}")
            self.llm = None
        
        # Initialize ChromaDB for RAG
        os.makedirs("./data/chroma_db", exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path="./data/chroma_db")
        self.collection = self.chroma_client.get_or_create_collection(
            name="sama_documents"
        )
        
        # Initialize Redis for conversation history
        try:
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                decode_responses=True
            )
            self.redis_client.ping()
            print("Redis connected for conversation history")
        except:
            self.redis_client = None
            print("Redis not available - no conversation history")
        
        # Initialize base Agent
        super().__init__(
            name="ComplianceChatAgent",
            model=self.llm,
            description="Interactive compliance Q&A with RAG"
        )
        
        # Initialize Kafka
        self.kafka_handler = KafkaHandler()
        
        # Initialize database
        self.db_session = None
        try:
            self.db_session = get_database_session()
            print("Database connected")
        except:
            print("Database not available")
        
        # Conversation storage
        self.conversations = {}
        
        print("Compliance Chat Agent ready!")
    
    def chat(self, user_query: str, session_id: str = None) -> Dict[str, Any]:
        """
        Process user chat query with RAG
        
        Args:
            user_query: User's question
            session_id: Session ID for conversation history
            
        Returns:
            Response dictionary
        """
        
        if not session_id:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"\nUser Query: {user_query}")
        
        # Get conversation history
        history = self._get_conversation_history(session_id)
        
        # Retrieve relevant documents using RAG
        relevant_docs = self._retrieve_relevant_documents(user_query)
        
        # Generate response with context
        response = self._generate_response(user_query, relevant_docs, history)
        
        # Store in conversation history
        self._store_conversation(session_id, user_query, response)
        
        # Log chat interaction
        self._log_interaction(session_id, user_query, response)
        
        return {
            "session_id": session_id,
            "query": user_query,
            "response": response["answer"],
            "sources": response.get("sources", []),
            "confidence": response.get("confidence", 0.0),
            "timestamp": datetime.now().isoformat()
        }
    
    def _retrieve_relevant_documents(self, query: str, n_results: int = 5) -> List[Dict]:
        """
        Retrieve relevant documents using vector search (RAG)
        
        Args:
            query: User query
            n_results: Number of documents to retrieve
            
        Returns:
            List of relevant documents
        """
        
        try:
            # Search in ChromaDB
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            documents = []
            if results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    doc = {
                        "id": results['ids'][0][i],
                        "content": results['documents'][0][i] if results['documents'] else "",
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if 'distances' in results else 0
                    }
                    documents.append(doc)
            
            print(f"Retrieved {len(documents)} relevant documents")
            return documents
            
        except Exception as e:
            logger.error(f"Document retrieval error: {e}")
            return []
    
    def _generate_response(self, query: str, documents: List[Dict], history: List[Dict]) -> Dict:
        """
        Generate response using LLM with retrieved context
        
        Args:
            query: User query
            documents: Retrieved documents
            history: Conversation history
            
        Returns:
            Response dictionary
        """
        
        if not self.llm:
            return self._generate_fallback_response(query, documents)
        
        # Prepare context from retrieved documents
        context = "\n\n".join([
            f"Document {i+1}: {doc['content'][:500]}"
            for i, doc in enumerate(documents[:3])
        ])
        
        # Prepare conversation history
        history_text = ""
        if history:
            recent_history = history[-3:]  # Last 3 exchanges
            for h in recent_history:
                history_text += f"User: {h.get('query', '')}\n"
                history_text += f"Assistant: {h.get('response', '')}\n\n"
        
        # Create prompt
        prompt = f"""
        You are a SAMA compliance expert assistant. Answer the user's question based on the provided context.
        
        Context from compliance documents:
        {context}
        
        Previous conversation:
        {history_text}
        
        User Question: {query}
        
        Provide a helpful, accurate answer. If the context doesn't contain the answer, say so.
        Be specific about SAMA requirements when relevant.
        
        Answer:
        """
        
        try:
            # Get response from LLM
            response_text = self.llm.run(prompt)
            
            # Determine confidence based on document relevance
            confidence = 0.8 if documents else 0.3
            
            # Extract sources
            sources = [
                {
                    "document_id": doc['id'][:16],
                    "type": doc['metadata'].get('document_type', 'unknown')
                }
                for doc in documents[:3]
            ]
            
            return {
                "answer": response_text,
                "sources": sources,
                "confidence": confidence,
                "used_rag": True
            }
            
        except Exception as e:
            logger.error(f"LLM response error: {e}")
            return self._generate_fallback_response(query, documents)
    
    def _generate_fallback_response(self, query: str, documents: List[Dict]) -> Dict:
        """Generate response without LLM"""
        
        query_lower = query.lower()
        
        # Basic keyword-based responses
        if "kyc" in query_lower:
            answer = "KYC (Know Your Customer) requirements for SAMA compliance include: "
            answer += "1) Valid commercial registration, 2) National ID verification, "
            answer += "3) Bank account verification, 4) Business activity documentation."
        
        elif "document" in query_lower:
            answer = "Required documents for SAMA compliance: "
            answer += "Commercial Registration (CR), National ID, Bank Statements, "
            answer += "Tax Certificates, and Business License."
        
        elif "compliance" in query_lower and "score" in query_lower:
            answer = "Compliance score is calculated based on: "
            answer += "Document completeness (40%), Validation results (40%), "
            answer += "and Timeliness (20%). A score above 80% is considered compliant."
        
        elif "sama" in query_lower:
            answer = "SAMA (Saudi Arabian Monetary Authority) regulates financial institutions "
            answer += "in Saudi Arabia. Compliance requires proper documentation, "
            answer += "KYC procedures, and regular reporting."
        
        else:
            answer = "I can help with SAMA compliance questions. "
            answer += "Please ask about KYC requirements, required documents, "
            answer += "compliance scores, or specific SAMA regulations."
        
        # Add document context if available
        if documents:
            answer += f"\n\nI found {len(documents)} related documents in the system."
        
        return {
            "answer": answer,
            "sources": [],
            "confidence": 0.5,
            "used_rag": False
        }
    
    def _get_conversation_history(self, session_id: str) -> List[Dict]:
        """Get conversation history from Redis or memory"""
        
        if self.redis_client:
            try:
                history_key = f"chat:history:{session_id}"
                history_json = self.redis_client.get(history_key)
                if history_json:
                    return json.loads(history_json)
            except Exception as e:
                logger.error(f"Redis history retrieval error: {e}")
        
        # Fallback to memory
        return self.conversations.get(session_id, [])
    
    def _store_conversation(self, session_id: str, query: str, response: Dict):
        """Store conversation in history"""
        
        conversation_entry = {
            "query": query,
            "response": response["answer"],
            "timestamp": datetime.now().isoformat()
        }
        
        # Get existing history
        history = self._get_conversation_history(session_id)
        history.append(conversation_entry)
        
        # Store in Redis
        if self.redis_client:
            try:
                history_key = f"chat:history:{session_id}"
                self.redis_client.setex(
                    history_key,
                    7200,  # 2 hours TTL
                    json.dumps(history)
                )
            except Exception as e:
                logger.error(f"Redis storage error: {e}")
        
        # Store in memory as fallback
        self.conversations[session_id] = history
    
    def _log_interaction(self, session_id: str, query: str, response: Dict):
        """Log chat interaction for audit"""
        
        # Send to Kafka for audit logging
        self.kafka_handler.send_event(
            topic="chat-interaction",
            key=session_id,
            value={
                "session_id": session_id,
                "query": query,
                "response_preview": response["answer"][:200],
                "confidence": response.get("confidence", 0),
                "used_rag": response.get("used_rag", False),
                "timestamp": datetime.now().isoformat()
            }
        )
    
    def get_session_summary(self, session_id: str) -> Dict:
        """Get summary of a chat session"""
        
        history = self._get_conversation_history(session_id)
        
        if not history:
            return {
                "session_id": session_id,
                "message": "No conversation history found"
            }
        
        return {
            "session_id": session_id,
            "total_queries": len(history),
            "start_time": history[0]["timestamp"] if history else None,
            "last_query": history[-1]["query"] if history else None,
            "queries": [h["query"] for h in history]
        }


def test_chat_agent():
    """Test the Compliance Chat Agent"""
    
    print("\n" + "="*60)
    print("TESTING COMPLIANCE CHAT AGENT")
    print("="*60)
    
    # Create agent
    agent = SAMAComplianceChatAgent()
    
    # Test queries
    test_queries = [
        "What documents are needed for SAMA compliance?",
        "How is the compliance score calculated?",
        "What are the KYC requirements?",
        "Tell me about SAMA regulations",
        "What is the status of customer TEST_001?"
    ]
    
    session_id = "test_session_001"
    
    print(f"\nSession ID: {session_id}")
    print("-"*60)
    
    for query in test_queries:
        print(f"\n👤 User: {query}")
        
        # Get response
        result = agent.chat(query, session_id)
        
        print(f"🤖 Agent: {result['response'][:300]}...")
        
        if result.get('sources'):
            print(f"📚 Sources: {len(result['sources'])} documents")
        
        print(f"📊 Confidence: {result.get('confidence', 0):.1%}")
    
    # Get session summary
    print("\n" + "-"*60)
    summary = agent.get_session_summary(session_id)
    print(f"Session Summary:")
    print(f"  Total Queries: {summary['total_queries']}")
    print(f"  Start Time: {summary.get('start_time', 'N/A')}")
    
    print("\n✅ Compliance Chat Agent test complete!")


if __name__ == "__main__":
    test_chat_agent()