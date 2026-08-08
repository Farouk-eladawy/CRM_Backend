import sqlite3, json
conn = sqlite3.connect('chat_history.db')
cur = conn.cursor()
cur.execute("SELECT user_id, settings_json FROM user_settings WHERE user_id LIKE '%internal_assistant_session%' OR user_id = 'global'")
res = cur.fetchall()
print(json.dumps(res, indent=2, ensure_ascii=False))
