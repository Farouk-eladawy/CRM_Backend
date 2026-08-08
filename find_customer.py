import sqlite3

db = sqlite3.connect('chat_history.db')
c = db.cursor()
row = c.execute("SELECT chat_id, source, contact_name, last_message_time FROM conversations WHERE sender_identifier='28145804381680714'").fetchone()
print("Customer Details:", row)

if row:
    chat_id = row[0]
    print("\nLast 5 messages in this chat:")
    messages = c.execute("SELECT sender_type, text, timestamp FROM messages WHERE chat_id=? ORDER BY timestamp DESC LIMIT 5", (chat_id,)).fetchall()
    for m in messages:
        print(f"[{m[2]}] {m[0]}: {m[1][:100]}")
