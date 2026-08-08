import sqlite3
import sys

db_path = r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\chat_history.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("=== RECENT FACEBOOK AGENT MESSAGES ===")
c.execute("SELECT id, chat_id, text, timestamp FROM messages WHERE source='Facebook' AND sender_type='agent' ORDER BY timestamp DESC LIMIT 5")
for row in c.fetchall():
    print(row)

print("=== RECENT FACEBOOK CUSTOMER MESSAGES ===")
c.execute("SELECT id, chat_id, text, timestamp FROM messages WHERE source='Facebook' AND sender_type='customer' ORDER BY timestamp DESC LIMIT 5")
for row in c.fetchall():
    print(row)

conn.close()
