from ai_agent import AIAgent

agent = AIAgent()
chat_id = "fb2b821e-9e54-4727-b0cd-8825043e07b0"
print("Assigning chat:", chat_id)
agent.route_religious_message_to_agent(chat_id)

import sqlite3
db = sqlite3.connect('chat_history.db')
chat = db.execute("SELECT chat_id, lead_owner_user_id, lead_owner_name, location FROM conversations WHERE chat_id=?", (chat_id,)).fetchone()
print("Chat after assignment:", chat)
