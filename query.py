import sqlite3
conn = sqlite3.connect('chat_history.db')
cur = conn.cursor()
cur.execute("SELECT sender_type, text, timestamp FROM messages WHERE chat_id IN (SELECT chat_id FROM conversations WHERE booking_number = 'GYG996Z6XKY5') ORDER BY timestamp ASC")
rows = cur.fetchall()
for r in rows:
    print(r)
