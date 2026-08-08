import sqlite3
import json

db_path = r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\chat_history.db"
out_path = r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\output_result.txt"
try:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("""
    SELECT chat_id, text, timestamp, external_message_id, source, sender_type, status
    FROM messages 
    WHERE sender_type = 'agent' AND source = 'Facebook'
    ORDER BY timestamp DESC
    LIMIT 10
    """)

    rows = c.fetchall()
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(str(r) + "\n")
except Exception as e:
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("Error: " + str(e))
