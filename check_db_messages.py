import sqlite3
import json
import os

db_path = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\chat_history.db"

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # استخراج آخر 20 رسالة
    cursor.execute('''
        SELECT *
        FROM messages 
        ORDER BY timestamp DESC 
        LIMIT 20
    ''')
    
    rows = cursor.fetchall()
    messages = [dict(row) for row in rows]
    
    with open(r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\out_messages.json", "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)
        
except Exception as e:
    with open(r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\out_messages.json", "w", encoding="utf-8") as f:
        f.write(str(e))
finally:
    if 'conn' in locals():
        conn.close()
