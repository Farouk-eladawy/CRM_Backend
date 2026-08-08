import sqlite3
import json

c = sqlite3.connect('chat_history.db')
c.row_factory = sqlite3.Row

# Get all messages from the last 2 hours
rows = c.execute("""
    SELECT m.timestamp, c.contact_name, c.booking_number, c.sender_identifier, m.text 
    FROM messages m 
    JOIN conversations c ON m.chat_id = c.chat_id 
    WHERE m.sender_type='customer' AND m.timestamp > '2026-07-27T13:00:00' 
    ORDER BY m.timestamp DESC
""").fetchall()

for r in rows:
    print(f"[{r['timestamp']}] {r['contact_name']} ({r['booking_number']}) [{r['sender_identifier']}]: {r['text'][:60].replace(chr(10), ' ')}")
