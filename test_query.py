import sqlite3, json
conn = sqlite3.connect('chat_history.db')
cur = conn.cursor()
cur.execute("SELECT text, sender_type, timestamp FROM messages WHERE chat_id IN (SELECT chat_id FROM conversations WHERE sender_identifier LIKE '%201010323484%') ORDER BY timestamp DESC LIMIT 10")
res = cur.fetchall()
print(json.dumps(res, indent=2, ensure_ascii=False))
