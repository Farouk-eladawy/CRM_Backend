import sqlite3

db = sqlite3.connect('chat_history.db')
chat = db.execute("SELECT chat_id, sender_identifier, lead_owner_user_id, lead_owner_name, location FROM conversations WHERE chat_id LIKE '%27571879472467252%' OR sender_identifier LIKE '%27571879472467252%'").fetchone()
print("Chat Details:", chat)

messages = db.execute("SELECT chat_id, sender_type, text, timestamp FROM messages WHERE chat_id LIKE '%27571879472467252%' ORDER BY timestamp DESC LIMIT 5").fetchall()
print("Messages:")
for m in messages:
    print(m)
