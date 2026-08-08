import sqlite3
import sys
sys.path.append('.')
from ai_agent import AIAgent

conn = sqlite3.connect('chat_history.db')
conn.row_factory = sqlite3.Row

# Reset incorrectly assigned Religious chats
conn.execute("UPDATE conversations SET lead_owner_user_id = NULL, lead_owner_name = NULL WHERE location='Religious' AND lead_owner_name IN ('Admin Manager', 'Mohamed Sami')")
conn.commit()

chats = conn.execute("SELECT chat_id FROM conversations WHERE location='Religious' AND (lead_owner_user_id IS NULL OR lead_owner_user_id = '')").fetchall()
agent = AIAgent()
for c in chats:
    agent.route_religious_message_to_agent(c['chat_id'])
    print(f"Routed {c['chat_id']}")
