import sqlite3
import traceback
import sys

out_path = r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\db_output_correct2.txt"
try:
    db_path = r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\chat_history.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT msg_id, chat_id, sender_type, text, timestamp, status, source 
        FROM messages 
        WHERE sender_type = 'agent' AND source = 'Facebook'
        ORDER BY timestamp DESC 
        LIMIT 20
    ''')
    rows = cursor.fetchall()
    
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(f"Found {len(rows)} rows\n")
        import json
        for row in rows:
            f.write(json.dumps(dict(row), ensure_ascii=False) + '\n')
            
    conn.close()
except Exception as e:
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write("ERROR:\n")
        f.write(traceback.format_exc())
