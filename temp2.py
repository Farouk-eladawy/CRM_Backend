import sqlite3
import json

c = sqlite3.connect('chat_history.db')
res = c.execute("SELECT value FROM user_settings WHERE key='dashboard_users'").fetchone()
if res:
    users = json.loads(res[0])
    for u in users:
        if u['username'] == 'test_user':
            if 'Transport' in u.get('allowedLocations', []):
                u['allowedLocations'].remove('Transport')
    
    new_val = json.dumps(users)
    c.execute("UPDATE user_settings SET value = ? WHERE key = 'dashboard_users'", (new_val,))
    c.commit()
    print("Updated successfully")
