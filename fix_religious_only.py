import sqlite3
import json
import re

DB_FILE = 'chat_history.db'

def main():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # جلب المستخدمين
    c.execute("SELECT value FROM user_settings WHERE key='dashboard_users'")
    row = c.fetchone()
    if not row:
        print("No dashboard users found.")
        return
    
    users = json.loads(row['value'])
    
    # فلترة مستخدمي القسم الديني فقط
    religious_agents = [u for u in users if 'Religious' in (u.get('allowedLocations') or [])]
    
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

    # إضافة أسماء مستخدمي القسم الديني للقاموس
    for u in religious_agents:
        agent_mapping[u['name'].lower()] = (str(u['id']), u['name'])
        first_name = u['name'].split()[0].lower()
        if first_name not in agent_mapping:
            agent_mapping[first_name] = (str(u['id']), u['name'])

    # تحديد المحادثات: فيسبوك + القسم الديني فقط
    c.execute("SELECT chat_id FROM conversations WHERE source='Facebook' AND location='Religious'")
    conversations = c.fetchall()

    updated_count = 0
    cleared_count = 0

    for conv in conversations:
        chat_id = conv['chat_id']
        
        # البحث في رسائل المحادثة
        c.execute("SELECT text FROM messages WHERE chat_id = ? AND sender_type = 'agent' ORDER BY timestamp DESC", (chat_id,))
        messages = c.fetchall()
        
        found_agent_id = None
        found_agent_name = None
        
        for msg in messages:
            text = msg['text'] or ""
            
            # البحث فقط عن "مع حضرتك"
            match = re.search(r'مع حضرتك\s+([^\s:]+)', text)
            if match:
                extracted = match.group(1).strip().lower()
                for key, val in agent_mapping.items():
                    if key in extracted or extracted in key:
                        found_agent_id, found_agent_name = val
                        break
            
            if found_agent_id:
                break

        if found_agent_id:
            # ربط المحادثة بالموظف الديني
            c.execute("UPDATE conversations SET lead_owner_user_id = ?, lead_owner_name = ? WHERE chat_id = ?", 
                      (found_agent_id, found_agent_name, chat_id))
            updated_count += 1
        else:
            # تم إيقاف تفريغ المحادثة لمنع سحب المحادثات من الموظفين بعد التوزيع التلقائي
            # c.execute("UPDATE conversations SET lead_owner_user_id = NULL, lead_owner_name = NULL WHERE chat_id = ?", (chat_id,))
            pass

    conn.commit()
    conn.close()
    
    print(f"Religious Facebook Chats -> Reassigned: {updated_count} | Cleared for Round-Robin: {cleared_count}")

if __name__ == "__main__":
    main()
