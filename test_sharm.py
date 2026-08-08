import sqlite3
conn = sqlite3.connect('chat_history.db')
c = conn.cursor()
c.execute("SELECT count(*) FROM conversations WHERE location='Sharm'")
print("Sharm chats:", c.fetchone()[0])
