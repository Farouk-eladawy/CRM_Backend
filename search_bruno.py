import sqlite3
import json

c = sqlite3.connect('chat_history.db')
c.row_factory = sqlite3.Row

# Get recent emails
rows = c.execute("SELECT m.chat_id, m.timestamp, m.text, c.contact_name, c.booking_number, c.source, c.sender_identifier FROM messages m JOIN conversations c ON m.chat_id = c.chat_id WHERE m.sender_type='customer' AND c.source='Email' AND m.timestamp > '2026-07-26' ORDER BY m.timestamp DESC").fetchall()
for r in rows:
    if 'bruno' in str(r['text']).lower() or 'charlyne' in str(r['text']).lower() or 'charlyn' in str(r['text']).lower():
        print(f"[{r['timestamp']}] {r['contact_name']} ({r['booking_number']}): {r['text'][:150].replace(chr(10), ' ')}")
    if r['booking_number'] is None or r['booking_number'] == 'None' or r['booking_number'] == '':
        print(f"Unlinked Email: [{r['timestamp']}] {r['contact_name']}: {r['text'][:150].replace(chr(10), ' ')}")
