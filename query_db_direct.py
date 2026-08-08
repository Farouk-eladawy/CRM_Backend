import sqlite3
import os

db_path = r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\chat_history.db"
if not os.path.exists(db_path):
    print("DB not found at:", db_path)
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
    print(f"Found {len(rows)} agent messages from Facebook.")
    for r in rows:
        print(dict(r))
        
    # Check recent Facebook messages overall
    cursor.execute('''
        SELECT id, chat_id, sender_type, source, text, timestamp 
        FROM messages 
        WHERE source = 'Facebook'
        ORDER BY timestamp DESC LIMIT 10
    ''')
    rows2 = cursor.fetchall()
    print("\nRecent 10 Facebook messages (any sender_type):")
    for r in rows2:
        print(dict(r))
        
    conn.close()