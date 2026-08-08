import sqlite3
conn = sqlite3.connect('chat_history.db')
c = conn.cursor()
c.execute("SELECT location, COUNT(*) FROM conversations WHERE receiving_phone_id = '560373790489064' GROUP BY location")
for row in c.fetchall():
    print(row)
conn.close()
