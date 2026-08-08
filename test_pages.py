import sqlite3
import json

db_path = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\chat_history.db"

try:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT DISTINCT receiving_phone_id FROM conversations WHERE source='Facebook'")
    rows = c.fetchall()
    print([r[0] for r in rows])
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
