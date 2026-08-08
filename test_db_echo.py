import sqlite3
try:
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("SELECT timestamp, chat_id, text FROM messages WHERE sender_type='agent' AND source='Facebook' ORDER BY timestamp DESC LIMIT 5")
    rows = c.fetchall()
    with open('test_db_echo.txt', 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(str(r) + '\n')
except Exception as e:
    with open('test_db_echo.txt', 'w', encoding='utf-8') as f:
        f.write(str(e))
