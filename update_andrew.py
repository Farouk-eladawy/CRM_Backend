import sqlite3

conn = sqlite3.connect('chat_history.db')
c = conn.cursor()
c.execute("UPDATE conversations SET airtable_record_id='rec2krDVjNpoRktqC' WHERE contact_name LIKE '%Andrew Mirman%' OR sender_identifier LIKE '%not-597b8128%'")
conn.commit()
print('Updated to correct Airtable ID!')
