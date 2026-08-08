import sqlite3
c = sqlite3.connect('chat_history.db')
print("Latest 5 convs:")
for r in c.execute("SELECT chat_id, last_message_time FROM conversations ORDER BY last_message_time DESC LIMIT 5").fetchall():
    print(r)
