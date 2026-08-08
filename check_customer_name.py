import sqlite3
import json

db_path = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\chat_history.db"

target_id = "25879763984995048"

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT chat_id, contact_name, location, lead_owner_name FROM conversations WHERE sender_identifier = ?", (target_id,))
    row = c.fetchone()
    
    if row:
        print(json.dumps(dict(row), ensure_ascii=False, indent=2))
    else:
        print("Not found")
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
