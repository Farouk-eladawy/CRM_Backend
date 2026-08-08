import sqlite3, json
db=sqlite3.connect('chat_history.db')
users = json.loads(db.execute("SELECT value FROM user_settings WHERE key='dashboard_users'").fetchone()[0])
for u in users:
    if 'Religious' in (u.get('allowedLocations') or []):
        print(f"User: {u.get('name')}, Shift: {u.get('shiftStart')} - {u.get('shiftEnd')}, Additional: {u.get('additionalShifts')}")
