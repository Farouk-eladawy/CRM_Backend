import sqlite3, json
conn = sqlite3.connect('chat_history.db')
row = conn.execute('SELECT value FROM user_settings WHERE key=\"dashboard_users\"').fetchone()
if row:
    users = json.loads(row[0])
    for u in users:
        print(f"{u.get('name')} | {u.get('allowedLocations')} | {u.get('workingDays')} | {u.get('shiftStart')} - {u.get('shiftEnd')}")
