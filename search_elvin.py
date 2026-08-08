import sqlite3
import json

c = sqlite3.connect('chat_history.db')
c.row_factory = sqlite3.Row

# Search for Elvin Kurtul
rows = c.execute("SELECT chat_id, source, sender_identifier, contact_name, booking_number, airtable_record_id FROM conversations WHERE contact_name LIKE '%Elvin%' OR contact_name LIKE '%Kurtul%'").fetchall()
print("Conversations with name Elvin Kurtul:")
print(json.dumps([dict(r) for r in rows], indent=2))
