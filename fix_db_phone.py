import sqlite3
conn = sqlite3.connect('chat_history.db')
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM conversations WHERE receiving_phone_id = '565029450024439'")
print("Count with 565029450024439:", c.fetchone()[0])
c.execute("UPDATE conversations SET receiving_phone_id = '560373790489064' WHERE receiving_phone_id = '565029450024439'")
conn.commit()
print("Updated rows:", c.rowcount)
conn.close()
