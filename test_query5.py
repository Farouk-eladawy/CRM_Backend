import sqlite3, json
conn = sqlite3.connect('chat_history.db')
cur = conn.cursor()
cur.execute("SELECT key, value FROM user_settings WHERE key LIKE '%internal_assistant_session%'")
res = cur.fetchall()
for k, v in res:
    try:
        data = json.loads(v)
        print("KEY:", k)
        print("RECENT TURNS:")
        print(json.dumps(data.get('recent_turns', []), indent=2, ensure_ascii=False))
    except:
        pass
