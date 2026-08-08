import sqlite3
import json

db_path = 'chat_history.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

booking_num = 'GYGZGZXYNLWF'

cursor.execute("""
    SELECT chat_id, source, sender_identifier, contact_name, airtable_record_id, location, booking_number, is_deleted, sales_inbox, department 
    FROM conversations 
    WHERE booking_number LIKE ? OR chat_id IN (SELECT chat_id FROM messages WHERE text LIKE ?)
""", (f'%{booking_num}%', f'%{booking_num}%'))

rows = [dict(row) for row in cursor.fetchall()]
print(f"Conversations for {booking_num}:")
print(json.dumps(rows, indent=2))

cursor.execute("""
    SELECT msg_id, chat_id, sender_type, timestamp, text
    FROM messages
    WHERE chat_id IN (SELECT chat_id FROM conversations WHERE booking_number LIKE ?) OR text LIKE ?
    ORDER BY timestamp ASC
""", (f'%{booking_num}%', f'%{booking_num}%'))

msgs = [dict(row) for row in cursor.fetchall()]
print(f"\nMessages for {booking_num} (Total: {len(msgs)}):")
for m in msgs:
    print(f"[{m['timestamp']}] {m['chat_id']} | {m['sender_type']}: {m['text'][:150].replace(chr(10), ' ')}...")
