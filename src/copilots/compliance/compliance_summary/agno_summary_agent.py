# src/copilots/compliance/compliance_summary/agno_summary_agent.py
"""
Compliance Summary Agent for SAMA Compliance
Generates compliance summaries for customers
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
from shared.models import ComplianceSummary, KYCValidation, Document, get_database_session, create_tables

# Import ChromaDB
import chromadb

# Import Redis
import redis

# Logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SAMAComplianceSummaryAgent(Agent):
    """
    Compliance Summary Agent
    
    This agent:
    1. Aggregates all documents for a customer
    2. Checks validation results
    3. Generates compliance summary
    4. Creates recommendations
    5. Stores and sends reports
    """
    
    def __init__(self):
        """Initialize Compliance Summary Agent"""
        
        print("Starting Compliance Summary Agent...")
        
        # Initialize Ollama LLM
        try:
            self.llm = OllamaForAgno(
                model="mistral",
                base_url="http://localhost:11434"
            )
        except Exception as e:
            print(f"Warning: Ollama not initialized: {e}")
            self.llm = None
        
        # Initialize ChromaDB
        os.makedirs("./data/chroma_db", exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path="./data/chroma_db")
        self.collection = self.chroma_client.get_or_create_collection(
            name="sama_documents"
        )
        
        # Initialize Redis
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
            name="ComplianceSummaryAgent",
            model=self.llm,
            description="Generates compliance summaries for customers"
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
        
        print("Compliance Summary Agent ready!")
    
    def generate_summary(self, customer_id: str) -> Dict[str, Any]:
        """
        Generate compliance summary for a customer
        
        Args:
            customer_id: Customer ID
            
        Returns:
            Summary dictionary
        """
        
        print(f"Generating compliance summary for customer: {customer_id}")
        
        # Check cache
        if self.redis_client:
            cached = self._get_from_cache(f"summary:{customer_id}")
            if cached:
                print("Returning cached summary")
                return cached
        
        # Retrieve all customer documents
        documents = self._get_customer_documents(customer_id)
        
        # Retrieve validation results
        validations = self._get_validation_results(customer_id)
        
        # Calculate compliance scores
        scores = self._calculate_scores(documents, validations)
        
        # Generate summary with AI
        summary_text = self._generate_ai_summary(customer_id, documents, validations, scores)
        
        # Prepare summary result
        summary_id = hashlib.md5(
            f"{customer_id}_{datetime.now()}".encode()
        ).hexdigest()
        
        result = {
            "summary_id": summary_id,
            "customer_id": customer_id,
            "total_documents": len(documents),
            "validated_documents": len(validations),
            "compliant_documents": scores['compliant_count'],
            "overall_compliance_score": scores['overall_score'],
            "compliance_status": scores['status'],
            "summary_text": summary_text,
            "issues": scores['all_issues'],
            "recommendations": scores['all_recommendations'],
            "generated_at": datetime.now().isoformat()
        }
        
        # Store summary
        self._store_summary(result)
        
        # Cache result
        if self.redis_client:
            self._save_to_cache(f"summary:{customer_id}", result)
        
        # Send events
        self._send_events(result)
        
        print(f"Summary generated: {scores['status']}")
        return result
    
    def _get_customer_documents(self, customer_id: str) -> List[Dict]:
        """Get all documents for a customer"""
        
        documents = []
        
        # Try database first
        if self.db_session:
            try:
                docs = self.db_session.query(Document).filter_by(
                    customer_id=customer_id
                ).all()
                
                for doc in docs:
                    documents.append({
                        "id": doc.id,
                        "type": doc.document_type,
                        "compliant": doc.sama_compliant,
                        "processed_at": doc.processed_at
                    })
            except Exception as e:
                logger.error(f"Database query error: {e}")
        
        # Try ChromaDB as fallback
        if not documents:
            try:
                results = self.collection.query(
                    query_texts=[f"customer {customer_id}"],
                    n_results=100,
                    where={"customer_id": customer_id}
                )
                
                for i, doc_id in enumerate(results['ids'][0]):
                    metadata = results['metadatas'][0][i]
                    documents.append({
                        "id": doc_id,
                        "type": metadata.get('document_type', 'unknown'),
                        "compliant": metadata.get('sama_compliant', 'false') == 'true'
                    })
            except Exception as e:
                logger.error(f"ChromaDB query error: {e}")
        
        return documents
    
    def _get_validation_results(self, customer_id: str) -> List[Dict]:
        """Get all validation results for a customer"""
        
        validations = []
        
        if self.db_session:
            try:
                vals = self.db_session.query(KYCValidation).filter_by(
                    customer_id=customer_id
                ).all()
                
                for val in vals:
                    validations.append({
                        "id": val.id,
                        "document_id": val.document_id,
                        "status": val.validation_status,
                        "score": val.validation_score,
                        "identity_verified": val.identity_verified,
                        "address_verified": val.address_verified,
                        "business_verified": val.business_verified
                    })
            except Exception as e:
                logger.error(f"Validation query error: {e}")
        
        return validations
    
    def _calculate_scores(self, documents: List[Dict], validations: List[Dict]) -> Dict:
        """Calculate compliance scores"""
        
        total_docs = len(documents)
        compliant_count = sum(1 for doc in documents if doc.get('compliant', False))
        
        # Calculate validation scores
        validation_scores = [v['score'] for v in validations if 'score' in v]
        avg_validation_score = sum(validation_scores) / len(validation_scores) if validation_scores else 0
        
        # Overall compliance score
        if total_docs > 0:
            doc_compliance_rate = compliant_count / total_docs
            overall_score = (doc_compliance_rate * 0.6) + (avg_validation_score * 0.4)
        else:
            overall_score = 0
        
        # Determine status
        if overall_score >= 0.8:
            status = "compliant"
        elif overall_score >= 0.6:
            status = "partially_compliant"
        else:
            status = "non_compliant"
        
        # Collect all issues and recommendations
        all_issues = []
        all_recommendations = []
        
        # Check for missing document types
        doc_types = [doc['type'] for doc in documents]
        required_types = ['commercial_registration', 'national_id', 'bank_statement']
        
        for req_type in required_types:
            if req_type not in doc_types:
                all_issues.append(f"Missing {req_type.replace('_', ' ')}")
                all_recommendations.append(f"Provide {req_type.replace('_', ' ')}")
        
        # Check validation issues
        for val in validations:
            if val['status'] != 'passed':
                all_issues.append(f"Document {val['document_id'][:8]} validation failed")
        
        return {
            "overall_score": overall_score,
            "compliant_count": compliant_count,
            "status": status,
            "all_issues": all_issues,
            "all_recommendations": all_recommendations
        }
    
    def _generate_ai_summary(self, customer_id: str, documents: List, 
                            validations: List, scores: Dict) -> str:
        """Generate AI-powered summary text"""
        
        if not self.llm:
            return self._generate_basic_summary(customer_id, documents, validations, scores)
        
        prompt = f"""
        Generate a compliance summary report for customer {customer_id}.
        
        Documents: {len(documents)} total
        - Commercial Registration: {'Yes' if any(d['type'] == 'commercial_registration' for d in documents) else 'No'}
        - National ID: {'Yes' if any(d['type'] == 'national_id' for d in documents) else 'No'}
        - Bank Statement: {'Yes' if any(d['type'] == 'bank_statement' for d in documents) else 'No'}
        
        Validation Results: {len(validations)} validated
        Overall Score: {scores['overall_score']:.2f}
        Status: {scores['status']}
        
        Issues: {', '.join(scores['all_issues'][:3]) if scores['all_issues'] else 'None'}
        
        Generate a professional summary in 3-4 sentences explaining:
        1. Current compliance status
        2. What's complete
        3. What's needed for full compliance
        """
        
        try:
            response = self.llm.run(prompt)
            return response
        except Exception as e:
            logger.error(f"AI summary generation error: {e}")
            return self._generate_basic_summary(customer_id, documents, validations, scores)
    
    def _generate_basic_summary(self, customer_id: str, documents: List, 
                               validations: List, scores: Dict) -> str:
        """Generate basic summary without AI"""
        
        summary = f"Compliance Summary for Customer {customer_id}: "
        summary += f"Status is {scores['status'].replace('_', ' ')} "
        summary += f"with {scores['compliant_count']} of {len(documents)} documents compliant. "
        summary += f"Overall compliance score: {scores['overall_score']:.1%}. "
        
        if scores['all_issues']:
            summary += f"Main issues: {', '.join(scores['all_issues'][:2])}. "
        
        if scores['all_recommendations']:
            summary += f"Next steps: {', '.join(scores['all_recommendations'][:2])}."
        
        return summary
    
    def _store_summary(self, summary: Dict):
        """Store summary in database"""
        
        if self.db_session:
            try:
                # Check if summary exists for customer
                existing = self.db_session.query(ComplianceSummary).filter_by(
                    customer_id=summary['customer_id']
                ).first()
                
                if existing:
                    # Update existing
                    existing.total_documents = summary['total_documents']
                    existing.compliant_documents = summary['compliant_documents']
                    existing.overall_compliance_score = summary['overall_compliance_score']
                    existing.compliance_status = summary['compliance_status']
                    existing.summary_text = summary['summary_text']
                    existing.issues_summary = json.dumps(summary['issues'])
                    existing.recommendations_summary = json.dumps(summary['recommendations'])
                    existing.updated_at = datetime.now()
                else:
                    # Create new
                    new_summary = ComplianceSummary(
                        id=summary['summary_id'],
                        customer_id=summary['customer_id'],
                        total_documents=summary['total_documents'],
                        compliant_documents=summary['compliant_documents'],
                        overall_compliance_score=summary['overall_compliance_score'],
                        compliance_status=summary['compliance_status'],
                        summary_text=summary['summary_text'],
                        issues_summary=json.dumps(summary['issues']),
                        recommendations_summary=json.dumps(summary['recommendations'])
                    )
                    self.db_session.add(new_summary)
                
                self.db_session.commit()
                print("Summary stored in database")
                
            except Exception as e:
                logger.error(f"Database storage error: {e}")
                self.db_session.rollback()
        else:
            if hasattr(self, 'memory_storage'):
                self.memory_storage[summary['summary_id']] = summary
    
    def _send_events(self, summary: Dict):
        """Send Kafka events"""
        
        self.kafka_handler.send_event(
            topic="compliance-summary-generated",
            key=summary['customer_id'],
            value={
                "summary_id": summary['summary_id'],
                "customer_id": summary['customer_id'],
                "status": summary['compliance_status'],
                "score": summary['overall_compliance_score'],
                "generated_at": summary['generated_at']
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


def test_summary_agent():
    """Test the Compliance Summary Agent"""
    
    print("\n" + "="*60)
    print("TESTING COMPLIANCE SUMMARY AGENT")
    print("="*60)
    
    # Create agent
    agent = SAMAComplianceSummaryAgent()
    
    # Generate summary for test customer
    result = agent.generate_summary("TEST_CUSTOMER_001")
    
    # Display results
    print("\n" + "-"*60)
    print("COMPLIANCE SUMMARY:")
    print("-"*60)
    print(f"Summary ID: {result.get('summary_id', 'N/A')[:16]}...")
    print(f"Customer: {result.get('customer_id')}")
    print(f"Status: {result.get('compliance_status')}")
    print(f"Score: {result.get('overall_compliance_score', 0):.2%}")
    print(f"Total Documents: {result.get('total_documents')}")
    print(f"Compliant Documents: {result.get('compliant_documents')}")
    
    print("\nSummary Text:")
    print(result.get('summary_text', 'No summary'))
    
    if result.get('issues'):
        print("\nIssues:")
        for issue in result['issues'][:5]:
            print(f"  - {issue}")
    
    if result.get('recommendations'):
        print("\nRecommendations:")
        for rec in result['recommendations'][:5]:
            print(f"  - {rec}")
    
    print("\n✅ Compliance Summary Agent test complete!")


if __name__ == "__main__":
    test_summary_agent()