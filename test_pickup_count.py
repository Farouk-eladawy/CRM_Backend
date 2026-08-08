import sqlite3

conn = sqlite3.connect('chat_history.db')
c = conn.cursor()
c.execute("SELECT text FROM messages WHERE chat_id='58733b28-7891-4248-ace7-b0bab541cffa' AND text LIKE '%Flight Pickup Template Sent%' LIMIT 1")
msgs = c.fetchall()
print(msgs[0][0])
