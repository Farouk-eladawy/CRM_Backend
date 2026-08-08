import sqlite3

def run_deletion():
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()

    # إنشاء جدول مؤقت لتخزين معرفات المحادثات القديمة بناءً على تاريخ آخر رسالة للعميل
    c.execute("""
        CREATE TEMP TABLE old_chats AS
        SELECT c.chat_id
        FROM conversations c
        WHERE NOT EXISTS (
            -- نستبعد المحادثات التي تحتوي على رسالة للعميل بعد يوم 19/7/2026
            SELECT 1 FROM messages m
            WHERE m.chat_id = c.chat_id
              AND m.sender_type = 'customer'
              AND substr(m.timestamp, 1, 10) > '2026-07-19'
        )
    """)

    # أولاً: حذف جميع الرسائل التابعة لهذه المحادثات القديمة
    c.execute("""
        DELETE FROM messages 
        WHERE chat_id IN (SELECT chat_id FROM old_chats)
    """)
    deleted_msgs = c.rowcount

    # ثانياً: حذف المحادثات القديمة نفسها
    c.execute("""
        DELETE FROM conversations 
        WHERE chat_id IN (SELECT chat_id FROM old_chats)
    """)
    deleted_convs = c.rowcount

    conn.commit()
    conn.close()

    print(f"تم بنجاح حذف {deleted_convs} محادثة و {deleted_msgs} رسالة من قاعدة البيانات.")

if __name__ == '__main__':
    run_deletion()