import sqlite3

conn = sqlite3.connect('chat_history.db')
c = conn.cursor()

# Get details about the specific chat
c.execute("SELECT chat_id, last_message_time, lead_owner_assigned_at, location FROM conversations WHERE airtable_record_id = 'recC8A4zZATbiz7Iz'")
chat = c.fetchone()
print(f"Chat details (airtable_record_id=recC8A4zZATbiz7Iz): {chat}")

if not chat:
    c.execute("SELECT chat_id, last_message_time, lead_owner_assigned_at, location FROM conversations WHERE chat_id = 'recC8A4zZATbiz7Iz'")
    chat = c.fetchone()
    print(f"Chat details (chat_id=recC8A4zZATbiz7Iz): {chat}")

# Count old chats
c.execute("SELECT COUNT(*) FROM conversations WHERE substr(last_message_time, 1, 10) <= '2026-07-19' OR last_message_time IS NULL")
count = c.fetchone()[0]
print(f"Old conversations to delete (<= 2026-07-19 or NULL): {count}")

c.execute("SELECT COUNT(*) FROM messages WHERE chat_id IN (SELECT chat_id FROM conversations WHERE substr(last_message_time, 1, 10) <= '2026-07-19' OR last_message_time IS NULL)")
msgs_count = c.fetchone()[0]
print(f"Old messages to delete: {msgs_count}")
