import sqlite3
import traceback
import sys

try:
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("SELECT msg_id, chat_id, text, timestamp FROM messages WHERE sender_type='agent' AND source='Facebook' ORDER BY timestamp DESC LIMIT 5")
    rows = c.fetchall()
    with open('test3.txt', 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(str(r) + '\n')
    print("Wrote to test3.txt")
except Exception as e:
    with open('test3.txt', 'w', encoding='utf-8') as f:
        f.write(str(e) + '\n' + traceback.format_exc())
    print("Error:", e)
