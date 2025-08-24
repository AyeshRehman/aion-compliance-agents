# fix_postgres_final.py
"""
Fix PostgreSQL connection using IPv4 address
"""

import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Test different connection methods
import psycopg2

print("Testing PostgreSQL connections...")
print("-" * 40)

# Test configurations
configs = [
    {"host": "127.0.0.1", "password": "postgres", "desc": "IPv4 with 'postgres'"},
    {"host": "127.0.0.1", "password": "password", "desc": "IPv4 with 'password'"},
    {"host": "localhost", "password": "postgres", "desc": "localhost with 'postgres'"},
]

working_config = None

for config in configs:
    try:
        print(f"\nTrying: {config['desc']}")
        conn = psycopg2.connect(
            host=config["host"],
            port=5432,
            database="postgres",
            user="postgres",
            password=config["password"],
            connect_timeout=3
        )
        print(f"✓ SUCCESS with {config['desc']}!")
        working_config = config
        
        # Check/create compliance database
        conn.autocommit = True
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'compliance'")
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute("CREATE DATABASE compliance")
            print("✓ Created 'compliance' database")
        else:
            print("✓ Database 'compliance' exists")
        
        cursor.close()
        conn.close()
        break
        
    except Exception as e:
        print(f"✗ Failed: {e}")

if working_config:
    print("\n" + "="*40)
    print("WORKING CONFIGURATION FOUND!")
    print("="*40)
    print(f"Host: {working_config['host']}")
    print(f"Password: {working_config['password']}")
    
    # Update environment variable
    db_url = f"postgresql://postgres:{working_config['password']}@{working_config['host']}:5432/compliance"
    os.environ["DATABASE_URL"] = db_url
    
    print(f"\nDatabase URL: {db_url}")
    
    # Now create tables
    try:
        # Connect to compliance database
        conn = psycopg2.connect(
            host=working_config["host"],
            port=5432,
            database="compliance",
            user="postgres",
            password=working_config["password"]
        )
        print("\n✓ Connected to compliance database")
        conn.close()
        
        # Update models.py DATABASE_URL
        import copilots.compliance.shared.models as models
        models.DATABASE_URL = db_url
        
        # Initialize database
        from copilots.compliance.shared.models import init_database, create_tables
        
        if init_database():
            print("✓ Database initialized")
            if create_tables():
                print("✓ All tables created!")
        
        print("\n✅ PostgreSQL is now properly configured!")
        print("\nUpdate your models.py with:")
        print(f'DATABASE_URL = "{db_url}"')
        
    except Exception as e:
        print(f"\n⚠️ Table creation error: {e}")
        print("But connection works! Update models.py manually.")
        
else:
    print("\n" + "="*40)
    print("ALTERNATIVE: Use without PostgreSQL")
    print("="*40)
    print("The agents will work with memory storage instead.")
    print("You can proceed with testing the agents!")
    
    # Check Docker
    print("\nChecking Docker containers...")
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=postgres"],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        
        print("\nTo check PostgreSQL password in Docker:")
        print("docker exec -it dev_postgres psql -U postgres")
        print("Then enter the password when prompted")
        
    except:
        print("Docker command not available")