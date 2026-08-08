import sqlite3

conn = sqlite3.connect('chat_history.db')
c = conn.cursor()

# Get the chat_id for the record
c.execute("SELECT chat_id FROM conversations WHERE airtable_record_id = 'recI6TVRihRerMBBr' OR chat_id = 'recI6TVRihRerMBBr'")
chat = c.fetchone()
if not chat:
    print('Chat not found!')
else:
    chat_id = chat[0]
    
    # Find the proposed draft message using timestamp and chat_id
    c.execute("SELECT timestamp, text FROM messages WHERE chat_id = ? AND text LIKE '[PROPOSED_DRAFT]%' ORDER BY timestamp DESC LIMIT 1", (chat_id,))
    draft_msg = c.fetchone()
    
    if not draft_msg:
        print('Draft message not found!')
    else:
        msg_timestamp, text = draft_msg
        
        # New corrected Arabic draft
        corrected_draft = '''[PROPOSED_DRAFT] أهلاً بك يا فندم.
تسعدنا خدمتك في FTS Travels. بخصوص استفسارك عن رحلاتنا المتاحة، هل تفضل رحلات الحج أم رحلات العمرة؟

نحن نوفر برامج متنوعة تناسب احتياجاتك:
✈️ حج طيران اقتصادي: يبدأ من ٢٢٠ ألف جنيه — ١٧ يوم تقريبًا.
⭐ حج طيران تحسين: يبدأ من ٢٥٠ ألف جنيه — ١٩ يوم (إقامة ٧ أيام على ساحة الحرم).
🕋 عمرة الـ ٨ أيام: تبدأ من ٣٤,٧٥٠ جنيه (شامل الطيران والتأشيرة والباركود والإقامة).

هل قمت بأداء الفريضة من قبل أم هذه أول مرة؟ لكي أتمكن من ترشيح البرنامج الأنسب لك.

مع خالص التحية،
مسؤول المبيعات أيه محمد'''
        
        # Update the message
        c.execute("UPDATE messages SET text = ? WHERE chat_id = ? AND timestamp = ?", (corrected_draft, chat_id, msg_timestamp))
        conn.commit()
        print(f'تم تصحيح مسودة المحادثة بنجاح.')
