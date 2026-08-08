import sqlite3
conn = sqlite3.connect('chat_history.db')
c = conn.cursor()
c.execute("SELECT timestamp, text FROM messages WHERE sender_type='agent' AND source='Facebook' ORDER BY timestamp DESC LIMIT 5")
rows = c.fetchall()
with open('db_test_6.txt', 'w', encoding='utf-8') as f:
    f.write(repr(rows))
