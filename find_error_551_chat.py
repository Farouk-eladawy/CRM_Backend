import sqlite3

db = sqlite3.connect('chat_history.db')
chat_id_row = db.execute("SELECT chat_id FROM conversations WHERE sender_identifier='37355749337374005'").fetchone()

if chat_id_row:
    chat_id = chat_id_row[0]
    print(f"Chat ID: {chat_id}")
    rows = db.execute("SELECT sender_type, text, timestamp FROM messages WHERE chat_id=? ORDER BY timestamp ASC", (chat_id,)).fetchall()
    for r in rows:
        print(f"[{r[2]}] {r[0]}: {r[1]}")
else:
    print("Chat not found")
