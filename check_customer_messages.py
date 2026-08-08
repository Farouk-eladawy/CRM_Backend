import sqlite3
import json

db_path = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\chat_history.db"

target_id = "25879763984995048"

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get chat_id
    c.execute("SELECT chat_id FROM conversations WHERE sender_identifier = ?", (target_id,))
    row = c.fetchone()
    chat_id = row['chat_id']
    
    c.execute("SELECT sender_type, text, timestamp, source, staff_note FROM messages WHERE chat_id = ? ORDER BY timestamp DESC LIMIT 20", (chat_id,))
    messages = c.fetchall()
    
    print(json.dumps([dict(m) for m in messages], ensure_ascii=False, indent=2))
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
