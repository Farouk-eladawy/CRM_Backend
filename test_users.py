import sqlite3, json

conn = sqlite3.connect('chat_history.db')
c = conn.cursor()
c.execute("SELECT value FROM user_settings WHERE key='dashboard_users'")
row = c.fetchone()
if row:
    users = json.loads(row[0])
    for u in users:
        if 'Ahmady_Tester' in u.get('username', ''):
            print(json.dumps(u, indent=2))
else:
    print('None')
conn.close()
