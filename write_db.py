import sqlite3
import json

db_path = 'chat_history.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT sender_type, text, source, timestamp FROM messages ORDER BY timestamp DESC LIMIT 20")
rows = [dict(r) for r in cur.fetchall()]
with open("db_messages.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False)
