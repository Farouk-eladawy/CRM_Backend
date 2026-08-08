import sqlite3
import json

db_path = r"chat_history.db"

print("=== أحدث 10 رسائل في قاعدة البيانات ===")
try:
    with sqlite3.connect(db_path, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT sender_type, text, source, timestamp FROM messages ORDER BY timestamp DESC LIMIT 10")
        for r in cur.fetchall():
            print(dict(r))
except Exception as e:
    print("DB Error:", e)

print("\n=== أحدث سجلات الويب هوك (Webhooks) ===")
try:
    with open("fb_webhook_debug.jsonl", "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines[-5:]:
            print(line.strip()[:500]) # طباعة جزء من السجل لتجنب التكدس
except Exception as e:
    print("Log Error:", e)
