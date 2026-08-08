import sqlite3
import traceback

try:
    db_path = r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\chat_history.db"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT count(*) FROM messages WHERE sender_type='agent' AND source='Facebook'")
    count = c.fetchone()[0]
    
    c.execute("SELECT timestamp, text FROM messages WHERE sender_type='agent' AND source='Facebook' ORDER BY timestamp DESC LIMIT 5")
    rows = c.fetchall()
    
    with open(r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\db_debug_agent.txt", "w", encoding="utf-8") as f:
        f.write(f"Count: {count}\n")
        for r in rows:
            f.write(str(r) + "\n")
except Exception as e:
    with open(r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\db_debug_agent.txt", "w", encoding="utf-8") as f:
        f.write("ERROR: " + str(e) + "\n" + traceback.format_exc())
