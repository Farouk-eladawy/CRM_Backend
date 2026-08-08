import sqlite3

conn = sqlite3.connect('chat_history.db')
c = conn.cursor()

c.execute("SELECT timestamp, sender_type, text FROM messages WHERE chat_id = '5f4b79e8-8d3e-4457-8d30-5703c2fad5ba' ORDER BY timestamp ASC")
msgs = c.fetchall()
print("Messages for recC8A4zZATbiz7Iz:")
for m in msgs:
    print(f"[{m[0]}] {m[1]}: {m[2][:50]}...")
