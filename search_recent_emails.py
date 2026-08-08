import sqlite3
import json

c = sqlite3.connect('chat_history.db')
c.row_factory = sqlite3.Row

# Get recent emails
rows = c.execute("SELECT m.chat_id, m.timestamp, m.text, c.contact_name, c.booking_number, c.source FROM messages m JOIN conversations c ON m.chat_id = c.chat_id WHERE m.sender_type='customer' AND c.source='Email' ORDER BY m.timestamp DESC LIMIT 10").fetchall()
print("Recent customer emails:")
for r in rows:
    print(f"[{r['timestamp']}] {r['contact_name']} ({r['booking_number']}): {r['text'][:100].replace(chr(10), ' ')}")

