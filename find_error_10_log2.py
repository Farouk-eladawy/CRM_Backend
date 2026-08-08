import sqlite3

db = sqlite3.connect('chat_history.db')
chat_id_row = db.execute("SELECT chat_id, contact_name, last_message_time FROM conversations WHERE sender_identifier='28111416041787397'").fetchone()

if chat_id_row:
    chat_id = chat_id_row[0]
    print(f"Chat ID: {chat_id}")
    print(f"Customer Name: {chat_id_row[1]}")
    print(f"Last Customer Message Time: {chat_id_row[2]}")
    
    rows = db.execute("SELECT sender_type, text, timestamp FROM messages WHERE chat_id=? ORDER BY timestamp ASC", (chat_id,)).fetchall()
    for r in rows:
        print(f"[{r[2]}] {r[0]}: {r[1]}")
else:
    print("Chat not found")