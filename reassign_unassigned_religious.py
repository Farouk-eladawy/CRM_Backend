import sqlite3
import json
import re
from datetime import datetime

DB_FILE = 'chat_history.db'

def get_cairo_time():
    try:
        import pytz
        egypt_tz = pytz.timezone('Africa/Cairo')
        return datetime.now(egypt_tz).isoformat()
    except ImportError:
        return datetime.now().isoformat()

def main(dry_run=True):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 1. Fetch users
    c.execute("SELECT value FROM user_settings WHERE key='dashboard_users'")
    row = c.fetchone()
    if not row:
        print("No dashboard users found.")
        return
    
    users = json.loads(row['value'])
    religious_agents = [u for u in users if 'Religious' in (u.get('allowedLocations') or []) and u.get('role') == 'Agent']
    
    if not religious_agents:
        print("No religious agents found.")
        return

    # Sort agents to ensure consistent round-robin order
    religious_agents.sort(key=lambda x: str(x.get('id')))

    agent_mapping = {
        "ايه": ("1783095968049", "Aya Mohamed"),
        "احمدخليل": ("17", "Ahmed Khalil"),
        "احمد خليل": ("17", "Ahmed Khalil"),
        "ملك": ("1783096007121", "Malak Maher"),
        "حنادي": ("1783096103617", "hanady mohamed"),
        "هنادي": ("1783096103617", "hanady mohamed"),
        "عبدالرحمن ابراهيم": ("1783096060057", "Abdelrhman ibrahim"),
        "عبدالرحمن": ("1783096060057", "Abdelrhman ibrahim"),
        "عبد الرحمن": ("1783096060057", "Abdelrhman ibrahim"),
        "محمد سامي": ("15", "Mohamed Sami"),
        "محمدسامي": ("15", "Mohamed Sami")
    }

    for u in religious_agents:
        agent_mapping[u['name'].lower()] = (str(u['id']), u['name'])
        first_name = u['name'].split()[0].lower()
        if first_name not in agent_mapping:
            agent_mapping[first_name] = (str(u['id']), u['name'])

    # 2. Fetch unassigned religious chats
    c.execute("""
        SELECT chat_id 
        FROM conversations 
        WHERE location = 'Religious' 
        AND (lead_owner_user_id IS NULL OR lead_owner_user_id = '')
        AND (is_deleted = 0 OR is_deleted IS NULL)
        AND is_closed = 0
    """)
    conversations = c.fetchall()

    print(f"Found {len(conversations)} open unassigned Religious chats.")

    assigned_by_signature = 0
    assigned_by_round_robin = 0
    rr_index = 0

    now_iso = get_cairo_time()

    for conv in conversations:
        chat_id = conv['chat_id']
        
        # 3. Check for agent signature in all messages of the chat
        c.execute("SELECT text FROM messages WHERE chat_id = ? ORDER BY timestamp DESC", (chat_id,))
        messages = c.fetchall()
        
        found_agent_id = None
        found_agent_name = None
        
        for msg in messages:
            text = msg['text'] or ""
            clean_text = text.lower().replace("أ", "ا").replace("إ", "ا").replace("ة", "ه").replace("ى", "ي")
            
            # check aliases with word boundaries to prevent partial matches
            for alias, (a_id, a_name) in agent_mapping.items():
                clean_alias = alias.lower().replace("أ", "ا").replace("إ", "ا").replace("ة", "ه").replace("ى", "ي")
                pattern = r'\b' + re.escape(clean_alias) + r'\b'
                if re.search(pattern, clean_text):
                    found_agent_id = a_id
                    found_agent_name = a_name
                    break
            
            if found_agent_id:
                break

        if found_agent_id:
            # Assign by signature
            if not dry_run:
                c.execute("""
                    UPDATE conversations 
                    SET lead_owner_user_id = ?, lead_owner_name = ?, lead_owner_assigned_at = ? 
                    WHERE chat_id = ?
                """, (found_agent_id, found_agent_name, now_iso, chat_id))
            assigned_by_signature += 1
        else:
            # Assign by round robin
            agent = religious_agents[rr_index]
            found_agent_id = str(agent['id'])
            found_agent_name = agent['name']
            
            if not dry_run:
                c.execute("""
                    UPDATE conversations 
                    SET lead_owner_user_id = ?, lead_owner_name = ?, lead_owner_assigned_at = ? 
                    WHERE chat_id = ?
                """, (found_agent_id, found_agent_name, now_iso, chat_id))
            
            assigned_by_round_robin += 1
            rr_index = (rr_index + 1) % len(religious_agents)

    if not dry_run:
        conn.commit()
    conn.close()
    
    print(f"DRY RUN: {dry_run}")
    print(f"Total processed: {len(conversations)}")
    print(f"Assigned by Mention/Signature: {assigned_by_signature}")
    print(f"Assigned by Round Robin: {assigned_by_round_robin}")

if __name__ == "__main__":
    import sys
    dry_run = True
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        dry_run = False
    main(dry_run)
