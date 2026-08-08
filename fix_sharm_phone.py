import sqlite3
conn = sqlite3.connect('chat_history.db')
c = conn.cursor()
c.execute("UPDATE conversations SET receiving_phone_id = '569636126228931' WHERE location = 'Sharm' AND receiving_phone_id = '560373790489064'")
conn.commit()
print("Updated Sharm rows:", c.rowcount)
conn.close()
