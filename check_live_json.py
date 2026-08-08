import sqlite3
import json
import os

db_path = r"chat_history.db"

output = {}

try:
    with sqlite3.connect(db_path, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT sender_type, text, source, timestamp FROM messages ORDER BY timestamp DESC LIMIT 10")
        output['messages'] = [dict(r) for r in cur.fetchall()]
except Exception as e:
    output['db_error'] = str(e)

try:
    with open("fb_webhook_debug.jsonl", "r", encoding="utf-8") as f:
        lines = f.readlines()
        output['webhooks'] = [json.loads(line.strip()) for line in lines[-5:] if line.strip()]
except Exception as e:
    output['log_error'] = str(e)

with open("live_output.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
