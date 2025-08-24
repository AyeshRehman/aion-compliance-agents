import sqlite3
import json
from datetime import datetime

# Connect to database
conn = sqlite3.connect('./data/compliance.db')
cursor = conn.cursor()

# View audit logs table
cursor.execute("SELECT * FROM audit_logs ORDER BY occurred_at DESC LIMIT 10")
logs = cursor.fetchall()

print("Recent audit logs:")
for log in logs:
    print(f"Event: {log[1]}, Agent: {log[3]}, Status: {log[7]}, Time: {log[8]}")

conn.close()