import sqlite3, json
db = sqlite3.connect('chat_history.db')
users = json.loads(db.execute("SELECT value FROM user_settings WHERE key='dashboard_users'").fetchone()[0])
religious_users = [(u.get('id'), u.get('name')) for u in users if 'Religious' in (u.get('allowedLocations') or [])]
print(religious_users)
