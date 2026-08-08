import sqlite3
import json
import chat_db

def run():
    print("Starting assignment of unassigned religious chats...")
    # 1. Get religious users
    users_raw = chat_db.get_setting("dashboard_users")
    if not users_raw:
        print("No users found")
        return
    users = json.loads(users_raw)
    religious_users = [u for u in users if 'Religious' in (u.get('allowedLocations') or []) and u.get('role') == 'Agent']
    print(f"Found {len(religious_users)} religious agents.")

    # 2. Get unassigned chats
    with sqlite3.connect(chat_db.DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('''
            SELECT chat_id 
            FROM conversations 
            WHERE location = 'Religious' 
              AND lead_owner_user_id IS NULL
        ''')
        unassigned_chats = [row['chat_id'] for row in c.fetchall()]
    
    print(f"Found {len(unassigned_chats)} unassigned religious chats.")

    assigned_count = 0
    # 3. Review messages for each chat
    with sqlite3.connect(chat_db.DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        for chat_id in unassigned_chats:
            c.execute('SELECT text FROM messages WHERE chat_id = ? ORDER BY timestamp ASC', (chat_id,))
            messages = c.fetchall()
            
            assigned = False
            for msg in messages:
                text = str(msg['text'] or "")
                # Check for agent names
                for u in religious_users:
                    agent_name = u.get('name', '')
                    if not agent_name: continue
                    
                    # Exact match of the full name
                    if agent_name in text:
                        print(f"Chat {chat_id} assigned to {agent_name} (found full name in text)")
                        chat_db.assign_sales_lead(chat_id, u['id'], agent_name)
                        assigned = True
                        break
                    
                    # Try to match first name if it's somewhat unique (like أيه, ملك, هنادي)
                    first_name = agent_name.split()[0]
                    if first_name in ['أيه', 'ملك', 'هنادي'] and first_name in text:
                        print(f"Chat {chat_id} assigned to {agent_name} (found first name '{first_name}' in text)")
                        chat_db.assign_sales_lead(chat_id, u['id'], agent_name)
                        assigned = True
                        break
                        
                if assigned:
                    assigned_count += 1
                    break

    print(f"Finished! Assigned {assigned_count} chats. Left {len(unassigned_chats) - assigned_count} unassigned.")

if __name__ == '__main__':
    run()
