# test_document_agent_fixed.py
"""
Test script for Document Ingestion Agent with Ollama
This version sets environment variables to bypass API key warnings
"""

import os
import sys

# Set dummy environment variables to bypass Agno's API key checks
# These are not used since we're using Ollama, but Agno checks for them
os.environ["GROQ_API_KEY"] = "not_needed_using_ollama"
os.environ["OPENAI_API_KEY"] = "not_needed_using_ollama"

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Now import the agent (after setting env vars)
from copilots.compliance.document_ingestion.agno_document_agent_ollama import SAMADocumentIngestionAgent

def test_agent():
    """Test the document ingestion agent"""
    
    print("="*60)
    print("TESTING DOCUMENT INGESTION AGENT WITH OLLAMA")
    print("="*60)
    
    # Create agent
    print("\nStep 1: Creating agent...")
    try:
        agent = SAMADocumentIngestionAgent()
        print("Agent created successfully!")
    except Exception as e:
        print(f"Error creating agent: {e}")
        return
    
    # Create test document
    print("\nStep 2: Creating test document...")
    test_file = "test_document.txt"
    test_content = """
    Commercial Registration Certificate
    Kingdom of Saudi Arabia
    
    Company Name: Test Compliance Company LLC
    Registration Number: 1234567890
    Issue Date: January 1, 2024
    Expiry Date: December 31, 2024
    
    Business Activities: Technology and Compliance Services
    Capital: 1,000,000 SAR
    
    This certificate confirms that the above company is registered
    with the Ministry of Commerce in accordance with Saudi regulations.
    """
    
    with open(test_file, 'w') as f:
        f.write(test_content)
    print(f"Created test file: {test_file}")
    
    # Process document
    print("\nStep 3: Processing document...")
    try:
        result = agent.process_document(
            file_path=test_file,
            customer_id="TEST_CUSTOMER_001"
        )
        print("Document processed successfully!")
    except Exception as e:
        print(f"Error processing document: {e}")
        return
    
    # Display results
    print("\n" + "="*60)
    print("PROCESSING RESULTS:")
    print("="*60)
    
    # Show key results
    for key in ["status", "document_id", "filename", "customer_id", 
                "document_type", "confidence", "sama_compliant"]:
        if key in result:
            value = result[key]
            # Truncate long values
            if isinstance(value, str) and len(value) > 50:
                value = value[:50] + "..."
            print(f"{key}: {value}")
    
    # Show issues if any
    if "issues" in result and result["issues"]:
        print("\nIssues found:")
        for issue in result["issues"]:
            print(f"  - {issue}")
    
    # Show recommendations if any
    if "recommendations" in result and result["recommendations"]:
        print("\nRecommendations:")
        for rec in result["recommendations"]:
            print(f"  - {rec}")
    
    print("\n" + "="*60)
    print("TEST COMPLETE!")
    print("="*60)

if __name__ == "__main__":
    # First check if Ollama is running
    print("Checking prerequisites...")
    
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            models = response.json().get("models", [])
            if models:
                print(f"✓ Ollama is running with {len(models)} model(s)")
                for model in models:
                    print(f"  - {model['name']}")
            else:
                print("✗ Ollama is running but no models found")
                print("  Run: ollama pull mistral")
                sys.exit(1)
        else:
            print("✗ Ollama is not responding properly")
            sys.exit(1)
    except Exception as e:
        print("✗ Ollama is not running")
        print("  Please run: ollama serve")
        sys.exit(1)
    
    # Run the test
    print("\nStarting test...\n")
    test_agent()