import sqlite3
with sqlite3.connect("chat_history.db") as conn:
    c = conn.cursor()
    c.execute("SELECT chat_id FROM conversations WHERE source='whatsapp' LIMIT 1")
    print(c.fetchone()[0])
