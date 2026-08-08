import sqlite3
import json

db_path = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\chat_history.db"

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT chat_id, sender_identifier, contact_name, last_message_time FROM conversations WHERE source='Facebook' AND (contact_name='' OR contact_name='Guest' OR contact_name IS NULL) ORDER BY last_message_time DESC LIMIT 5")
    rows = c.fetchall()
    
    print(json.dumps([dict(r) for r in rows], indent=2))
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
