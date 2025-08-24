# final_integration_test.py
"""
Final Integration Test for SAMA Compliance Co-Pilot
This script performs a complete end-to-end test of all components
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Set environment variables
os.environ["GROQ_API_KEY"] = "not_needed"
os.environ["OPENAI_API_KEY"] = "not_needed"

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    """Print formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")

def print_section(text):
    """Print section header"""
    print(f"\n{Colors.BOLD}{'-'*60}{Colors.END}")
    print(f"{Colors.BOLD}{text}{Colors.END}")
    print(f"{Colors.BOLD}{'-'*60}{Colors.END}")

def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_info(text):
    """Print info message"""
    print(f"   {text}")

# ============================================================================
# INFRASTRUCTURE TESTS
# ============================================================================

def test_infrastructure() -> Tuple[Dict, bool]:
    """Test all infrastructure components"""
    
    print_section("INFRASTRUCTURE TEST")
    
    results = {}
    all_critical_working = True
    
    # Test 1: Ollama (CRITICAL)
    print("\n1. Testing Ollama LLM...")
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get("models", [])
            if models:
                results["Ollama"] = True
                print_success(f"Ollama is running with {len(models)} model(s)")
                for model in models:
                    print_info(f"Model: {model['name']}")
            else:
                results["Ollama"] = False
                print_error("Ollama is running but no models found")
                print_info("Run: ollama pull mistral")
                all_critical_working = False
        else:
            results["Ollama"] = False
            print_error("Ollama not responding properly")
            all_critical_working = False
    except Exception as e:
        results["Ollama"] = False
        print_error(f"Ollama not running: {e}")
        print_info("Start Ollama with: ollama serve")
        all_critical_working = False
    
    # Test 2: ChromaDB (CRITICAL)
    print("\n2. Testing ChromaDB Vector Database...")
    try:
        import chromadb
        os.makedirs("./data/chroma_db", exist_ok=True)
        client = chromadb.PersistentClient(path="./data/chroma_db")
        collection = client.get_or_create_collection("test_collection")
        count = collection.count()
        results["ChromaDB"] = True
        print_success(f"ChromaDB is working ({count} documents in test collection)")
    except Exception as e:
        results["ChromaDB"] = False
        print_error(f"ChromaDB error: {e}")
        all_critical_working = False
    
    # Test 3: Redis (OPTIONAL but recommended)
    print("\n3. Testing Redis Cache...")
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True, socket_connect_timeout=2)
        r.ping()
        # Test set and get
        r.set('test_key', 'test_value', ex=10)
        value = r.get('test_key')
        if value == 'test_value':
            results["Redis"] = True
            print_success("Redis is working and caching enabled")
        else:
            results["Redis"] = False
            print_warning("Redis connected but operations failed")
    except Exception as e:
        results["Redis"] = False
        print_warning(f"Redis not available: {e}")
        print_info("Agent will work without caching (slower but functional)")
    
    # Test 4: Database (OPTIONAL - has fallback)
    print("\n4. Testing Database...")
    try:
        from copilots.compliance.shared.models import test_database_connection, create_tables
        if test_database_connection():
            create_tables()
            results["Database"] = True
            print_success("Database connected and tables created")
        else:
            results["Database"] = False
            print_warning("Database not available - using memory storage")
    except Exception as e:
        results["Database"] = False
        print_warning(f"Database error: {e}")
        print_info("Using memory storage as fallback")
    
    # Test 5: Kafka (OPTIONAL - has mock)
    print("\n5. Testing Kafka Event System...")
    try:
        from copilots.compliance.shared.kafka_handler import KafkaHandler
        handler = KafkaHandler()
        
        if hasattr(handler, 'mock_events'):
            results["Kafka"] = "Mock"
            print_warning("Using Mock Kafka (real Kafka not running)")
            print_info("Events will be stored in memory")
        else:
            results["Kafka"] = True
            print_success("Real Kafka is connected")
    except Exception as e:
        results["Kafka"] = False
        print_error(f"Kafka handler error: {e}")
    
    return results, all_critical_working

# ============================================================================
# AGENT TESTS
# ============================================================================

def test_agents() -> Tuple[Dict, List]:
    """Test all 5 agents with a complete workflow"""
    
    print_section("AGENT INTEGRATION TEST")
    
    results = {}
    documents_created = []
    
    # Test 1: Document Ingestion Agent
    print("\n1. Testing Document Ingestion Agent...")
    try:
        from copilots.compliance.document_ingestion.agno_document_agent_ollama import SAMADocumentIngestionAgent
        
        doc_agent = SAMADocumentIngestionAgent()
        
        # Create multiple test documents
        test_docs = [
            {
                "filename": "commercial_registration.txt",
                "content": """
                COMMERCIAL REGISTRATION CERTIFICATE
                المملكة العربية السعودية
                
                Company Name: Saudi Tech Solutions LLC
                Registration Number: 1010567890
                Issue Date: 01/01/2024
                Expiry Date: 31/12/2024
                
                Business Activities: Information Technology and Compliance Services
                Authorized Capital: 10,000,000 SAR
                Paid Capital: 10,000,000 SAR
                
                Issued by: Ministry of Commerce
                Status: Active
                """
            },
            {
                "filename": "national_id.txt",
                "content": """
                NATIONAL IDENTITY CARD
                بطاقة الهوية الوطنية
                
                Name: Ahmed Abdullah Al-Rashid
                ID Number: 1234567890
                Date of Birth: 15/06/1985
                Nationality: Saudi Arabian
                
                Issue Date: 01/01/2020
                Expiry Date: 01/01/2030
                """
            },
            {
                "filename": "bank_statement.txt",
                "content": """
                BANK STATEMENT
                كشف حساب بنكي
                
                Account Holder: Saudi Tech Solutions LLC
                Account Number: 1234567890123456
                IBAN: SA1234567890123456789012
                
                Period: January 2024
                
                Opening Balance: 5,000,000 SAR
                Total Credits: 2,000,000 SAR
                Total Debits: 1,500,000 SAR
                Closing Balance: 5,500,000 SAR
                
                Bank: Saudi National Bank
                """
            }
        ]
        
        # Process each document
        for doc_info in test_docs:
            # Create file
            with open(doc_info["filename"], 'w', encoding='utf-8') as f:  # ✅ Fixed
                f.write(doc_info["content"])
            
            # Process document
            result = doc_agent.process_document(doc_info["filename"], "TEST_CUSTOMER_001")
            
            if result.get("status") == "success":
                documents_created.append({
                    "id": result["document_id"],
                    "type": result.get("document_type", "unknown"),
                    "filename": doc_info["filename"]
                })
                print_success(f"Processed {doc_info['filename']}: {result['document_id'][:16]}...")
                print_info(f"Type: {result.get('document_type', 'unknown')}")
                print_info(f"SAMA Compliant: {result.get('sama_compliant', False)}")
            else:
                print_error(f"Failed to process {doc_info['filename']}")
        
        results["Document Ingestion"] = len(documents_created) > 0
        
    except Exception as e:
        results["Document Ingestion"] = False
        print_error(f"Document Ingestion Agent error: {e}")
    
    # Test 2: KYC Validation Agent
    print("\n2. Testing KYC Validation Agent...")
    try:
        from copilots.compliance.kyc_validation.agno_kyc_agent import SAMAKYCValidationAgent
        
        kyc_agent = SAMAKYCValidationAgent()
        
        validations_completed = 0
        for doc in documents_created:
            try:
                validation = kyc_agent.validate_kyc(doc["id"], "TEST_CUSTOMER_001")
                if validation:
                    validations_completed += 1
                    print_success(f"Validated {doc['filename']}: {validation.get('validation_status', 'unknown')}")
                    print_info(f"Score: {validation.get('validation_score', 0):.2f}")
            except Exception as e:
                print_warning(f"Could not validate {doc['filename']}: {e}")
        
        results["KYC Validation"] = validations_completed > 0
        
    except Exception as e:
        results["KYC Validation"] = False
        print_error(f"KYC Validation Agent error: {e}")
    
    # Test 3: Compliance Summary Agent
    print("\n3. Testing Compliance Summary Agent...")
    try:
        from copilots.compliance.compliance_summary.agno_summary_agent import SAMAComplianceSummaryAgent
        
        summary_agent = SAMAComplianceSummaryAgent()
        summary = summary_agent.generate_summary("TEST_CUSTOMER_001")
        
        if summary:
            results["Compliance Summary"] = True
            print_success(f"Summary generated for TEST_CUSTOMER_001")
            print_info(f"Status: {summary.get('compliance_status', 'unknown')}")
            print_info(f"Overall Score: {summary.get('overall_compliance_score', 0):.2%}")
            print_info(f"Total Documents: {summary.get('total_documents', 0)}")
            
            # Print summary text
            if summary.get('summary_text'):
                print_info(f"Summary: {summary['summary_text'][:200]}...")
        else:
            results["Compliance Summary"] = False
            print_error("Failed to generate summary")
            
    except Exception as e:
        results["Compliance Summary"] = False
        print_error(f"Compliance Summary Agent error: {e}")
    
    # Test 4: Compliance Chat Agent
    print("\n4. Testing Compliance Chat Agent...")
    try:
        from copilots.compliance.compliance_chat.agno_chat_agent import SAMAComplianceChatAgent
        
        chat_agent = SAMAComplianceChatAgent()
        
        # Test queries
        test_queries = [
            "What documents are required for SAMA compliance?",
            "What is the compliance status of TEST_CUSTOMER_001?",
            "Explain the KYC requirements"
        ]
        
        successful_chats = 0
        session_id = f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        for query in test_queries:
            try:
                response = chat_agent.chat(query, session_id)
                if response and response.get('response'):
                    successful_chats += 1
                    print_success(f"Query: {query[:50]}...")
                    print_info(f"Response: {response['response'][:150]}...")
            except Exception as e:
                print_warning(f"Chat query failed: {e}")
        
        results["Compliance Chat"] = successful_chats > 0
        
    except Exception as e:
        results["Compliance Chat"] = False
        print_error(f"Compliance Chat Agent error: {e}")
    
    # Test 5: Audit Logging Agent
    print("\n5. Testing Audit Logging Agent...")
    try:
        from copilots.compliance.audit_logging.agno_audit_agent import SAMAAuditLoggingAgent
        
        audit_agent = SAMAAuditLoggingAgent()
        
        # Log some test events
        test_events = [
            ("document-processed", {"document_id": "test_001", "status": "success"}),
            ("kyc-validation-completed", {"validation_id": "val_001", "status": "passed"}),
            ("compliance-summary-generated", {"summary_id": "sum_001", "status": "success"}),
        ]
        
        events_logged = 0
        for event_type, event_data in test_events:
            try:
                result = audit_agent.log_event(event_type, {
                    **event_data,
                    "agent_name": "TestAgent",
                    "customer_id": "TEST_CUSTOMER_001"
                })
                if result.get('logged'):
                    events_logged += 1
            except:
                pass
        
        # Generate audit report
        report = audit_agent.get_audit_report(customer_id="TEST_CUSTOMER_001")
        
        if report:
            results["Audit Logging"] = True
            print_success(f"Logged {events_logged} events")
            print_info(f"Total events in report: {report.get('total_events', 0)}")
            print_info(f"Report generated: {report.get('report_id', 'N/A')}")
        else:
            results["Audit Logging"] = events_logged > 0
            
    except Exception as e:
        results["Audit Logging"] = False
        print_error(f"Audit Logging Agent error: {e}")
    
    return results, documents_created

# ============================================================================
# END-TO-END WORKFLOW TEST
# ============================================================================

def test_end_to_end_workflow():
    """Test complete workflow from document to audit"""
    
    print_section("END-TO-END WORKFLOW TEST")
    
    print("\nSimulating complete compliance workflow...")
    print_info("Document → KYC → Summary → Chat → Audit")
    
    try:
        # Step 1: Create and process a document
        print("\nStep 1: Processing new document...")
        from copilots.compliance.document_ingestion.agno_document_agent_ollama import SAMADocumentIngestionAgent
        
        doc_agent = SAMADocumentIngestionAgent()
        
        # Create test document
        test_file = "workflow_test_doc.txt"
        with open(test_file, 'w', encoding='utf-8') as f:  # ✅ Fixed
            f.write("""
            COMMERCIAL REGISTRATION - WORKFLOW TEST
            Company: Workflow Test Company
            Registration Number: 9999888877
            Capital: 15,000,000 SAR
            Issue Date: 01/01/2024
            """)
        
        doc_result = doc_agent.process_document(test_file, "WORKFLOW_CUSTOMER")
        
        if doc_result.get("status") == "success":
            print_success(f"Document processed: {doc_result['document_id'][:16]}...")
            
            # Step 2: Validate KYC
            print("\nStep 2: Validating KYC...")
            from copilots.compliance.kyc_validation.agno_kyc_agent import SAMAKYCValidationAgent
            
            kyc_agent = SAMAKYCValidationAgent()
            kyc_result = kyc_agent.validate_kyc(doc_result['document_id'], "WORKFLOW_CUSTOMER")
            
            if kyc_result:
                print_success(f"KYC validated: {kyc_result.get('validation_status', 'unknown')}")
                
                # Step 3: Generate summary
                print("\nStep 3: Generating compliance summary...")
                from copilots.compliance.compliance_summary.agno_summary_agent import SAMAComplianceSummaryAgent
                
                summary_agent = SAMAComplianceSummaryAgent()
                summary = summary_agent.generate_summary("WORKFLOW_CUSTOMER")
                
                if summary:
                    print_success(f"Summary generated: {summary.get('compliance_status', 'unknown')}")
                    
                    # Step 4: Chat interaction
                    print("\nStep 4: Testing chat interaction...")
                    from copilots.compliance.compliance_chat.agno_chat_agent import SAMAComplianceChatAgent
                    
                    chat_agent = SAMAComplianceChatAgent()
                    chat_response = chat_agent.chat(
                        "What is the status of WORKFLOW_CUSTOMER?",
                        "workflow_session"
                    )
                    
                    if chat_response:
                        print_success("Chat query successful")
                        
                        # Step 5: Check audit log
                        print("\nStep 5: Checking audit trail...")
                        from copilots.compliance.audit_logging.agno_audit_agent import SAMAAuditLoggingAgent
                        
                        audit_agent = SAMAAuditLoggingAgent()
                        audit_report = audit_agent.get_audit_report(customer_id="WORKFLOW_CUSTOMER")
                        
                        if audit_report:
                            print_success(f"Audit trail complete: {audit_report.get('total_events', 0)} events")
                            print_success("END-TO-END WORKFLOW SUCCESSFUL!")
                            return True
        
        print_error("End-to-end workflow incomplete")
        return False
        
    except Exception as e:
        print_error(f"Workflow error: {e}")
        return False

# ============================================================================
# MAIN TEST EXECUTION
# ============================================================================

def main():
    """Execute complete final integration test"""
    
    print_header("SAMA COMPLIANCE CO-PILOT - FINAL INTEGRATION TEST")
    print(f"\n{Colors.BOLD}Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
    
    # Track overall results
    test_results = {
        "infrastructure": {},
        "agents": {},
        "workflow": False,
        "timestamp": datetime.now().isoformat()
    }
    
    # Phase 1: Infrastructure
    print_header("PHASE 1: INFRASTRUCTURE")
    infra_results, critical_ok = test_infrastructure()
    test_results["infrastructure"] = infra_results
    
    if not critical_ok:
        print_error("\nCritical infrastructure missing!")
        print_info("Please ensure:")
        print_info("1. Ollama is running: ollama serve")
        print_info("2. Ollama has a model: ollama pull mistral")
        print_info("3. ChromaDB dependencies installed: pip install chromadb")
        return False
    
    # Phase 2: Agents
    print_header("PHASE 2: AGENTS")
    agent_results, documents = test_agents()
    test_results["agents"] = agent_results
    
    # Phase 3: Workflow
    print_header("PHASE 3: END-TO-END WORKFLOW")
    workflow_result = test_end_to_end_workflow()
    test_results["workflow"] = workflow_result
    
    # Final Report
    print_header("FINAL TEST REPORT")
    
    # Infrastructure Summary
    print_section("Infrastructure Summary")
    working_infra = sum(1 for v in infra_results.values() if v == True)
    total_infra = len(infra_results)
    print(f"Infrastructure: {working_infra}/{total_infra} components working")
    
    for component, status in infra_results.items():
        if status == True:
            print_success(component)
        elif status == "Mock":
            print_warning(f"{component} (using mock)")
        else:
            print_error(component)
    
    # Agent Summary
    print_section("Agent Summary")
    working_agents = sum(1 for v in agent_results.values() if v)
    total_agents = len(agent_results)
    print(f"Agents: {working_agents}/{total_agents} agents working")
    
    for agent, status in agent_results.items():
        if status:
            print_success(agent)
        else:
            print_error(agent)
    
    # Workflow Summary
    print_section("Workflow Summary")
    if workflow_result:
        print_success("End-to-end workflow completed successfully")
    else:
        print_warning("End-to-end workflow had issues")
    
    # Overall Result
    print_header("TEST RESULT")
    
    # Calculate success criteria
    all_agents_working = working_agents == 5
    critical_infra_working = infra_results.get("Ollama") and infra_results.get("ChromaDB")
    minimum_functionality = working_agents >= 3 and critical_infra_working
    
    if all_agents_working and critical_infra_working:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ ALL TESTS PASSED - SYSTEM FULLY OPERATIONAL!{Colors.END}")
        print_success("Your SAMA Compliance Co-Pilot is ready for production demo!")
        success = True
    elif minimum_functionality:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️ PARTIAL SUCCESS - SYSTEM OPERATIONAL WITH LIMITATIONS{Colors.END}")
        print_warning("Core functionality working but some features limited")
        success = True
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ TESTS FAILED - CRITICAL ISSUES DETECTED{Colors.END}")
        print_error("Please fix the issues above before proceeding")
        success = False
    
    # Save results
    os.makedirs("test_results", exist_ok=True)
    result_file = f"test_results/final_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_file, 'w') as f:
        json.dump(test_results, f, indent=2, default=str)
    
    print(f"\n{Colors.BOLD}Test results saved to: {result_file}{Colors.END}")
    print(f"{Colors.BOLD}Test Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
    
    # Cleanup test files
    print("\nCleaning up test files...")
    test_files = [
        "commercial_registration.txt", "national_id.txt", "bank_statement.txt",
        "workflow_test_doc.txt", "test_integration_doc.txt", "test_doc_1.txt"
    ]
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)
            print_info(f"Removed {file}")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)