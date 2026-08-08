import sqlite3
import ai_agent

conn = sqlite3.connect('chat_history.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT chat_id FROM conversations WHERE location='Religious' AND lead_owner_user_id IS NULL")
chats = c.fetchall()

print(f"Found {len(chats)} unassigned Religious chats. Routing them now...")

agent = ai_agent.AIAgent()
for row in chats:
    agent.route_religious_message_to_agent(row['chat_id'])

print("Routing complete.")
