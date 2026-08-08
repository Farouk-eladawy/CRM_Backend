import sqlite3
conn=sqlite3.connect('chat_history.db')
conn.execute("UPDATE conversations SET location='Guides' WHERE sender_identifier='201005138825'")
conn.commit()
conn.close()
