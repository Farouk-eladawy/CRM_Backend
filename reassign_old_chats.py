import sqlite3
import json
import re

DB_FILE = 'chat_history.db'

def main():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT value FROM user_settings WHERE key='dashboard_users'")
    row = c.fetchone()
    if not row:
        print("No dashboard users found.")
        return
    
    users = json.loads(row['value'])
    
    # We will build a mapping of lowercase parts to the user ID and Name
    agent_mapping = {
        "ايه": ("1783095968049", "Aya Mohamed"),
        "احمدخليل": ("17", "Ahmed Khalil"),
        "احمد خليل": ("17", "Ahmed Khalil"),
        "ملك": ("1783096007121", "Malak Maher"),
        "حنادي": ("1783096103617", "hanady mohamed"),
        "هنادي": ("1783096103617", "hanady mohamed"),
        "عبدالرحمن ابراهيم": ("1783096060057", "Abdelrhman ibrahim"),
        "عبدالرحمن": ("1783096060057", "Abdelrhman ibrahim"),
        "محمد سامي": ("15", "Mohamed Sami")
    }

    # Auto-map from users list
    for u in users:
        agent_mapping[u['name'].lower()] = (str(u['id']), u['name'])
        agent_mapping[u['username'].lower()] = (str(u['id']), u['name'])
        
        # Split name and add first name if unique enough
        first_name = u['name'].split()[0].lower()
        if first_name not in agent_mapping:
            agent_mapping[first_name] = (str(u['id']), u['name'])

    print("Agent mapping initialized.")

    c.execute("SELECT chat_id FROM conversations WHERE lead_owner_user_id IS NULL OR lead_owner_user_id != ''")
    conversations = c.fetchall()

    updated_count = 0

    for conv in conversations:
        chat_id = conv['chat_id']
        
        # Check messages for this chat
        c.execute("SELECT text FROM messages WHERE chat_id = ? AND sender_type = 'agent' ORDER BY timestamp DESC", (chat_id,))
        messages = c.fetchall()
        
        found_agent_id = None
        found_agent_name = None
        
        for msg in messages:
            text = msg['text'] or ""
            
            # 1. Check for "Replied via: Name"
            match_via = re.search(r'Replied via:\s*([^\s\n]+)', text)
            if match_via:
                extracted = match_via.group(1).strip().lower()
                for key, val in agent_mapping.items():
                    if key in extracted or extracted in key:
                        found_agent_id, found_agent_name = val
                        break
            
            # 2. Check for "مع حضرتك (اسم)"
            if not found_agent_id:
                match_7adretak = re.search(r'مع حضرتك\s+([^\s:]+)', text)
                if match_7adretak:
                    extracted = match_7adretak.group(1).strip().lower()
                    for key, val in agent_mapping.items():
                        if key in extracted or extracted in key:
                            found_agent_id, found_agent_name = val
                            break
            
            if found_agent_id:
                break

        if found_agent_id:
            c.execute("UPDATE conversations SET lead_owner_user_id = ?, lead_owner_name = ? WHERE chat_id = ?", 
                      (found_agent_id, found_agent_name, chat_id))
            updated_count += 1

    conn.commit()
    conn.close()
    
    print(f"Done. Reassigned {updated_count} chats based on signature.")

if __name__ == "__main__":
    main()
