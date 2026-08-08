import sqlite3
conn = sqlite3.connect('chat_history.db')
c = conn.cursor()
c.execute("DELETE FROM messages WHERE sender_type='customer' AND source IS NULL")
conn.commit()
print('Cleaned up duplicate customer messages.')
