import sqlite3
import json
import re

DB_FILE = 'chat_history.db'

def main():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # خريطة ذكية بالأسماء المحتملة للموظفين (بما فيها الأخطاء الإملائية أو المسافات)
    agent_aliases = {
        "احمدخليل": ("17", "Ahmed Khalil"),
        "احمد خليل": ("17", "Ahmed Khalil"),
        "أحمد خليل": ("17", "Ahmed Khalil"),
        "ملك": ("1783096007121", "Malak Maher"),
        "ايه": ("1783095968049", "Aya Mohamed"),
        "آيه": ("1783095968049", "Aya Mohamed"),
        "آية": ("1783095968049", "Aya Mohamed"),
        "هنادي": ("1783096103617", "hanady mohamed"),
        "حنادي": ("1783096103617", "hanady mohamed"),
        "عبدالرحمن": ("1783096060057", "Abdelrhman ibrahim"),
        "عبد الرحمن": ("1783096060057", "Abdelrhman ibrahim"),
        "محمد سامي": ("15", "Mohamed Sami"),
        "محمدسامي": ("15", "Mohamed Sami")
    }

    # استهداف كل محادثات القسم الديني من فيسبوك
    c.execute("SELECT chat_id FROM conversations WHERE source='Facebook' AND location='Religious'")
    conversations = c.fetchall()

    updated_count = 0

    for conv in conversations:
        chat_id = conv['chat_id']
        
        # جلب رسائل الصفحة (التي أرسلها الموظفون) لهذه المحادثة - من الأحدث للأقدم
        c.execute("SELECT text FROM messages WHERE chat_id = ? AND sender_type = 'agent' ORDER BY timestamp DESC", (chat_id,))
        messages = c.fetchall()
        
        found_agent_id = None
        found_agent_name = None
        
        for msg in messages:
            text = msg['text']
            if not text:
                continue
                
            # تنظيف النص وتوحيده للبحث
            clean_text = text.replace('\n', ' ').replace('\r', ' ')
            
            # التحقق من وجود كلمة تدل على أن هذا توقيع موظف
            if "مع حضرتك" in clean_text or "معاك" in clean_text or "معاكي" in clean_text:
                # البحث الذكي عن أي من الأسماء المستعارة داخل النص
                for alias, (a_id, a_name) in agent_aliases.items():
                    if alias in clean_text:
                        found_agent_id = a_id
                        found_agent_name = a_name
                        break
            
            if found_agent_id:
                break

        # إذا وجدنا الموظف، نقوم بتحديث المحادثة لتصبح ملكه
        if found_agent_id:
            c.execute("UPDATE conversations SET lead_owner_user_id = ?, lead_owner_name = ? WHERE chat_id = ?", 
                      (found_agent_id, found_agent_name, chat_id))
            updated_count += 1

    conn.commit()
    conn.close()
    
    print(f"Smart Sweep Completed! Successfully reassigned {updated_count} Religious Facebook chats based on agent signatures.")

if __name__ == "__main__":
    main()
