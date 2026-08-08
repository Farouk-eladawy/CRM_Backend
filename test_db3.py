import sqlite3
conn = sqlite3.connect('chat_history.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT msg_id, sender_type, text, timestamp, external_message_id FROM messages WHERE chat_id = 'fc863a55-6593-4de2-ab2c-0fb7e3f891f4' AND sender_type = 'customer' ORDER BY timestamp DESC LIMIT 15")
for r in c.fetchall():
    print(f"[{r['timestamp']}] {r['sender_type']} (ext_id: {r['external_message_id']}): {r['text'][:50]}")
