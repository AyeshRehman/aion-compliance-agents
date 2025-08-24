# test_services_docker.py
"""
Test services running in Docker containers
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_redis():
    """Test Redis connection"""
    print("Testing Redis...")
    try:
        import redis
        # Connect to Redis in Docker
        r = redis.Redis(
            host='localhost',
            port=6379,
            decode_responses=True,
            socket_connect_timeout=2
        )
        r.ping()
        # Test operations
        r.set('test_key', 'test_value', ex=10)
        value = r.get('test_key')
        if value == 'test_value':
            print("✓ Redis: Connected and working")
            return True
        else:
            print("✗ Redis: Connected but operations failed")
            return False
    except Exception as e:
        print(f"✗ Redis: {e}")
        print("  Trying to connect to Redis in Docker container...")
        try:
            # Try Docker container
            import subprocess
            result = subprocess.run(
                ["docker", "exec", "redis-sama", "redis-cli", "ping"],
                capture_output=True,
                text=True
            )
            if "PONG" in result.stdout:
                print("  Redis is running in Docker but Python can't connect")
                print("  Check firewall or Docker network settings")
            return False
        except:
            return False

def test_postgresql():
    """Test PostgreSQL connection"""
    print("Testing PostgreSQL...")
    try:
        import psycopg2
        # Connect to PostgreSQL in Docker
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="compliance",
            user="postgres",
            password="postgres",  # Default password from docker
            connect_timeout=3
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        conn.close()
        print(f"✓ PostgreSQL: Connected (version: {version[0][:20]}...)")
        
        # Create tables
        from copilots.compliance.shared.models import create_tables
        create_tables()
        print("  Tables created successfully")
        return True
        
    except Exception as e:
        print(f"✗ PostgreSQL: {e}")
        print("  Checking Docker container...")
        try:
            import subprocess
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=dev_postgres"],
                capture_output=True,
                text=True
            )
            if "dev_postgres" in result.stdout:
                print("  PostgreSQL container is running")
                print("  Try password: 'password' or check docker-compose.yml")
            return False
        except:
            return False

def test_kafka():
    """Test Kafka connection"""
    print("Testing Kafka...")
    try:
        from kafka import KafkaProducer
        from kafka.errors import NoBrokersAvailable
        
        # Try to connect
        producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            api_version_auto_timeout_ms=5000,
            max_block_ms=5000
        )
        
        # Send test message
        future = producer.send('test-topic', b'test-message')
        result = future.get(timeout=5)
        producer.close()
        
        print("✓ Kafka: Connected and working")
        return True
        
    except NoBrokersAvailable:
        print("✗ Kafka: No brokers available")
        print("  Kafka is not running or not accessible")
        print("  Starting Kafka may take a minute after container starts")
        return False
    except Exception as e:
        print(f"✗ Kafka: {e}")
        # Check if container exists
        try:
            import subprocess
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", "name=kafka"],
                capture_output=True,
                text=True
            )
            if "kafka" in result.stdout:
                print("  Kafka container exists, checking logs:")
                subprocess.run(["docker", "logs", "--tail", "5", "dev_kafka"])
            else:
                print("  No Kafka container found")
        except:
            pass
        return False

def test_ollama():
    """Test Ollama connection"""
    print("Testing Ollama...")
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get("models", [])
            if models:
                print(f"✓ Ollama: Running with {len(models)} model(s)")
                for model in models:
                    print(f"    - {model['name']}")
                return True
            else:
                print("✗ Ollama: No models found")
                print("  Run: ollama pull mistral")
                return False
    except Exception as e:
        print(f"✗ Ollama: Not running ({e})")
        print("  Start with: ollama serve")
        return False

def test_chromadb():
    """Test ChromaDB"""
    print("Testing ChromaDB...")
    try:
        import chromadb
        # Create client
        client = chromadb.PersistentClient(path="./data/chroma_db")
        # Get or create collection
        collection = client.get_or_create_collection("test")
        count = collection.count()
        print(f"✓ ChromaDB: Working ({count} documents)")
        return True
    except Exception as e:
        print(f"✗ ChromaDB: {e}")
        return False

def check_docker_containers():
    """Check running Docker containers"""
    print("\nDocker Containers Status:")
    print("-" * 40)
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"],
            capture_output=True,
            text=True
        )
        print(result.stdout)
    except Exception as e:
        print(f"Could not check Docker: {e}")

def main():
    """Run all tests"""
    print("="*60)
    print("SAMA COMPLIANCE - SERVICE CHECK")
    print("="*60)
    
    # Check Docker containers first
    check_docker_containers()
    
    print("\nTesting Services:")
    print("-" * 40)
    
    results = {
        "Ollama": test_ollama(),
        "PostgreSQL": test_postgresql(),
        "Redis": test_redis(),
        "Kafka": test_kafka(),
        "ChromaDB": test_chromadb()
    }
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for service, status in results.items():
        status_text = "✓ Working" if status else "✗ Not Working"
        print(f"{service:15} {status_text}")
    
    # Determine readiness
    critical = results["Ollama"] and results["ChromaDB"]
    optimal = all(results.values())
    
    print("\n" + "="*60)
    if optimal:
        print("✅ ALL SERVICES WORKING - Ready for production!")
    elif critical and results["PostgreSQL"] and results["Redis"]:
        print("⚠️  Most services working - Kafka needs attention")
        print("\nTo fix Kafka:")
        print("1. docker rm dev_kafka")
        print("2. Use the kafka-simple.yml provided")
        print("3. docker-compose -f kafka-simple.yml up -d")
    elif critical:
        print("⚠️  Core services working - Can proceed with limited functionality")
    else:
        print("❌ Critical services missing")
    
    return optimal

if __name__ == "__main__":
    success = main()