import sqlite3

conn = sqlite3.connect('chat_history.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("SELECT * FROM conversations WHERE sender_identifier = '27730973183236119' OR chat_id = '27730973183236119' OR chat_id = 'fc863a55-6593-4de2-ab2c-0fb7e3f891f4'")
chat = c.fetchone()

if chat:
    print(f"Chat found: chat_id={chat['chat_id']}, sender_identifier={chat['sender_identifier']}, location={chat['location']}")
    c.execute("SELECT msg_id, sender_type, text, timestamp FROM messages WHERE chat_id = ? ORDER BY timestamp DESC LIMIT 20", (chat['chat_id'],))
    messages = c.fetchall()
    for m in messages:
        text = m['text'].replace('\n', '\\n')
        print(f"[{m['timestamp']}] {m['sender_type']}: {text[:100]}")
else:
    print("Chat not found.")
