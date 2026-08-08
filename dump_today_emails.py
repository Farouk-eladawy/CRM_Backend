import sqlite3

c = sqlite3.connect('chat_history.db')
c.row_factory = sqlite3.Row

rows = c.execute("SELECT m.timestamp, c.contact_name, c.booking_number, m.text FROM messages m JOIN conversations c ON m.chat_id = c.chat_id WHERE m.sender_type='customer' AND m.timestamp > '2026-07-27' AND c.source='Email' ORDER BY m.timestamp DESC").fetchall()

for r in rows:
    print(f"[{r['timestamp']}] {r['contact_name']} ({r['booking_number']}): {r['text'][:50].replace(chr(10), ' ')}")
