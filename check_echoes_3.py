import json
import sqlite3

try:
    with sqlite3.connect('chat_history.db') as conn:
        c = conn.cursor()
        c.execute("SELECT timestamp, text, source FROM messages WHERE sender_type='agent' AND source='Facebook' ORDER BY timestamp DESC LIMIT 20")
        rows = c.fetchall()
        with open('echoes_out_3.txt', 'w', encoding='utf-8') as f:
            for r in rows:
                f.write(str(r) + '\n')
except Exception as e:
    with open('echoes_out_3.txt', 'w', encoding='utf-8') as f:
        f.write(str(e))
