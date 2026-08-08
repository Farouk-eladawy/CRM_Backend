import sqlite3
import json
import os

print(os.getcwd())
db_path = r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\chat_history.db"

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print('--- LATEST 10 MESSAGES ---')
cursor.execute('''
    SELECT id, chat_id, message_text, sender_id, sender_type, timestamp, is_echo 
    FROM messages 
    ORDER BY timestamp DESC 
    LIMIT 10
''')
for row in cursor.fetchall():
    print(json.dumps(dict(row), ensure_ascii=False))

print('\n--- LATEST 5 AGENT/ECHO MESSAGES ---')
cursor.execute('''
    SELECT id, chat_id, message_text, sender_id, sender_type, timestamp, is_echo 
    FROM messages 
    WHERE sender_type = 'agent' OR is_echo = 1
    ORDER BY timestamp DESC 
    LIMIT 5
''')
for row in cursor.fetchall():
    print(json.dumps(dict(row), ensure_ascii=False))

conn.close()
