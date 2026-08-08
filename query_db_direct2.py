import sqlite3
import os

db_path = r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\chat_history.db"
out_path = r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\db_out4.txt"

with open(out_path, 'w', encoding='utf-8') as f:
    if not os.path.exists(db_path):
        f.write("DB not found at: " + db_path + "\n")
    else:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check recent agent messages from Facebook
        cursor.execute('''
            SELECT id, chat_id, sender_type, source, text, timestamp 
            FROM messages 
            WHERE source = 'Facebook' AND sender_type = 'agent' 
            ORDER BY timestamp DESC LIMIT 20
        ''')
        rows = cursor.fetchall()
        f.write(f"Found {len(rows)} agent messages from Facebook.\n")
        for r in rows:
            f.write(str(dict(r)) + "\n")
            
        # Check recent Facebook messages overall
        cursor.execute('''
            SELECT id, chat_id, sender_type, source, text, timestamp 
            FROM messages 
            WHERE source = 'Facebook'
            ORDER BY timestamp DESC LIMIT 10
        ''')
        rows2 = cursor.fetchall()
        f.write("\nRecent 10 Facebook messages (any sender_type):\n")
        for r in rows2:
            f.write(str(dict(r)) + "\n")
            
        conn.close()
