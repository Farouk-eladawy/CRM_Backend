import sqlite3, json
conn = sqlite3.connect('chat_history.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print(cur.fetchall())
cur.execute("SELECT key, value FROM settings WHERE key LIKE 'internal_assistant_session%'")
res = cur.fetchall()
print(json.dumps(res, indent=2, ensure_ascii=False))
