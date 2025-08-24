# test_services.py
"""
Test all required services for SAMA Compliance Co-Pilot
This ensures Redis, Kafka, PostgreSQL, and Ollama are working
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_redis():
    """Test Redis connection"""
    try:
        import redis
        r = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True,
            socket_connect_timeout=2
        )
        r.ping()
        # Test set and get
        r.set('test_key', 'test_value', ex=10)
        value = r.get('test_key')
        print("✓ Redis: Connected and working")
        return True
    except Exception as e:
        print(f"✗ Redis: {e}")
        return False

def test_postgresql():
    """Test PostgreSQL connection"""
    try:
        from copilots.compliance.shared.models import test_database_connection, create_tables
        
        if test_database_connection():
            create_tables()
            print("✓ PostgreSQL: Connected and tables created")
            return True
        else:
            print("✗ PostgreSQL: Connection failed")
            return False
    except Exception as e:
        print(f"✗ PostgreSQL: {e}")
        return False

def test_kafka():
    """Test Kafka connection"""
    try:
        from kafka import KafkaProducer, KafkaConsumer
        from kafka.errors import NoBrokersAvailable
        
        # Test producer
        producer = KafkaProducer(
            bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
            value_serializer=lambda v: str(v).encode('utf-8')
        )
        
        # Send test message
        future = producer.send('test-topic', value='test-message')
        result = future.get(timeout=5)
        
        producer.close()
        print("✓ Kafka: Connected and working")
        return True
        
    except NoBrokersAvailable:
        print("✗ Kafka: No brokers available (not running)")
        return False
    except Exception as e:
        print(f"✗ Kafka: {e}")
        return False

def test_ollama():
    """Test Ollama connection"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            models = response.json().get("models", [])
            if models:
                print(f"✓ Ollama: Running with {len(models)} model(s)")
                return True
            else:
                print("✗ Ollama: No models found (run: ollama pull mistral)")
                return False
        else:
            print("✗ Ollama: Not responding")
            return False
    except Exception as e:
        print(f"✗ Ollama: {e}")
        return False

def test_chromadb():
    """Test ChromaDB (Pinecone replacement)"""
    try:
        import chromadb
        client = chromadb.PersistentClient(path="./data/chroma_db")
        collection = client.get_or_create_collection("test")
        count = collection.count()
        print(f"✓ ChromaDB: Working ({count} documents)")
        return True
    except Exception as e:
        print(f"✗ ChromaDB: {e}")
        return False

def main():
    """Run all tests"""
    print("="*60)
    print("SAMA COMPLIANCE CO-PILOT - SERVICE CHECK")
    print("="*60)
    print("\nTesting all required services...\n")
    
    results = {
        "Ollama (LLM)": test_ollama(),
        "PostgreSQL (Database)": test_postgresql(),
        "Redis (Cache)": test_redis(),
        "Kafka (Events)": test_kafka(),
        "ChromaDB (Vectors)": test_chromadb()
    }
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    all_working = all(results.values())
    required_working = results["Ollama (LLM)"] and results["ChromaDB (Vectors)"]
    
    for service, status in results.items():
        status_text = "✓ Working" if status else "✗ Not Working"
        print(f"{service:25} {status_text}")
    
    print("\n" + "="*60)
    
    if all_working:
        print("✅ ALL SERVICES WORKING - Ready for full deployment!")
    elif required_working:
        print("⚠️  Core services working - Can proceed with limited functionality")
        print("\nTo enable full functionality:")
        if not results["PostgreSQL (Database)"]:
            print("  - Install PostgreSQL or use Docker")
        if not results["Redis (Cache)"]:
            print("  - Install Redis or use Docker")
        if not results["Kafka (Events)"]:
            print("  - Install Kafka or use Docker")
    else:
        print("❌ Critical services missing - Cannot proceed")
        if not results["Ollama (LLM)"]:
            print("  - Start Ollama: ollama serve")
            print("  - Pull model: ollama pull mistral")
    
    return all_working

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)