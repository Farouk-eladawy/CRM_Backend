import sqlite3
import json
import os
import traceback

out_path = os.path.join(os.getcwd(), 'db_output_123.txt')
db_path = os.path.join(os.getcwd(), 'chat_history.db')

try:
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('--- START ---\n')
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        f.write('--- LATEST 10 MESSAGES ---\n')
        cursor.execute('''
            SELECT id, chat_id, message_text, sender_id, sender_type, timestamp, is_echo 
            FROM messages 
            ORDER BY timestamp DESC 
            LIMIT 10
        ''')
        for row in cursor.fetchall():
            f.write(json.dumps(dict(row), ensure_ascii=False) + '\n')
            
        f.write('\n--- LATEST 5 AGENT/ECHO MESSAGES ---\n')
        cursor.execute('''
            SELECT id, chat_id, message_text, sender_id, sender_type, timestamp, is_echo 
            FROM messages 
            WHERE sender_type = 'agent' OR is_echo = 1
            ORDER BY timestamp DESC 
            LIMIT 5
        ''')
        for row in cursor.fetchall():
            f.write(json.dumps(dict(row), ensure_ascii=False) + '\n')
            
        conn.close()
        f.write('--- END ---\n')
except Exception as e:
    with open(out_path, 'a', encoding='utf-8') as f:
        f.write('\nERROR: ' + traceback.format_exc() + '\n')
