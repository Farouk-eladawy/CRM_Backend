import sqlite3
import os

DB_PATH = "chat_history.db"

def fix_db():
    if not os.path.exists(DB_PATH):
        print("Database not found.")
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check how many have the WABA ID instead of Phone Number ID
    cursor.execute("SELECT count(*) FROM conversations WHERE receiving_phone_id = '560373790489064'")
    hurghada_bad = cursor.fetchone()[0]
    
    cursor.execute("SELECT count(*) FROM conversations WHERE receiving_phone_id = '569636126228931'")
    sharm_bad = cursor.fetchone()[0]
    
    print(f"Chats with Hurghada WABA ID: {hurghada_bad}")
    print(f"Chats with Sharm WABA ID: {sharm_bad}")
    
    # Also check the old fallback one just in case
    cursor.execute("SELECT count(*) FROM conversations WHERE receiving_phone_id = '565029450024439'")
    old_bad = cursor.fetchone()[0]
    print(f"Chats with old bad ID (565029450024439): {old_bad}")
    
    # Fix them
    cursor.execute("UPDATE conversations SET receiving_phone_id = '1077199985483939' WHERE receiving_phone_id = '560373790489064'")
    cursor.execute("UPDATE conversations SET receiving_phone_id = '1060037273868859' WHERE receiving_phone_id = '569636126228931'")
    cursor.execute("UPDATE conversations SET receiving_phone_id = '1077199985483939' WHERE receiving_phone_id = '565029450024439'")
    
    conn.commit()
    print("Database updated successfully.")
    conn.close()

if __name__ == '__main__':
    fix_db()
