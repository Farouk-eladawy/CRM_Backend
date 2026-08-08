import sqlite3
conn=sqlite3.connect('chat_history.db')
conn.execute("UPDATE conversations SET airtable_record_id = NULL, booking_number = NULL WHERE sender_identifier = '201005138825'")
conn.commit()
conn.close()
