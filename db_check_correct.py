import sqlite3
import json

db_path = r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\chat_history.db"
out_path = r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\db_output_correct.txt"

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute('''
    SELECT msg_id, chat_id, sender_type, text, timestamp, status, source 
    FROM messages 
    WHERE sender_type = 'agent' AND source = 'Facebook'
    ORDER BY timestamp DESC 
    LIMIT 20
''')

with open(out_path, 'w', encoding='utf-8') as f:
    for row in cursor.fetchall():
        f.write(json.dumps(dict(row), ensure_ascii=False) + '\n')

conn.close()
