import sqlite3, json
conn = sqlite3.connect('chat_history.db')
cur = conn.cursor()
cur.execute("SELECT key, value FROM user_settings WHERE key LIKE '%internal_assistant_session%'")
res = cur.fetchall()
for k, v in res:
    print("KEY:", k)
    print("VALUE:", v)
