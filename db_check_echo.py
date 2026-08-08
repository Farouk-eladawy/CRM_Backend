import sqlite3
import json
import sys

db_path = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\chat_history.db"

try:
    with open(r"c:\Users\Aloosh2020\output.txt", "w", encoding="utf-8") as f:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        f.write("--- RECENT MESSAGES (SENDER_TYPE='agent') ---\n")
        cur.execute("SELECT id, chat_id, sender_type, text, timestamp FROM messages WHERE sender_type = 'agent' ORDER BY timestamp DESC LIMIT 5")
        for r in cur.fetchall():
            f.write(json.dumps(dict(r), ensure_ascii=False) + "\n")

        f.write("\n--- RECENT MESSAGES (ALL) ---\n")
        cur.execute("SELECT id, chat_id, sender_type, text, timestamp FROM messages ORDER BY timestamp DESC LIMIT 5")
        for r in cur.fetchall():
            f.write(json.dumps(dict(r), ensure_ascii=False) + "\n")
            
        f.write("\n--- SEARCHING FOR 'هيتم التواصل' ---\n")
        cur.execute("SELECT id, chat_id, sender_type, text, timestamp FROM messages WHERE text LIKE '%هيتم التواصل%' ORDER BY timestamp DESC LIMIT 5")
        for r in cur.fetchall():
            f.write(json.dumps(dict(r), ensure_ascii=False) + "\n")

        conn.close()
except Exception as e:
    with open(r"c:\Users\Aloosh2020\output.txt", "w", encoding="utf-8") as f:
        f.write("Error: " + str(e))
