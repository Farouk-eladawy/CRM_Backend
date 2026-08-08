import chat_db
import json

users_raw = chat_db.get_setting("dashboard_users")
users = json.loads(users_raw) if users_raw else []
for u in users:
    if 'Religious' in (u.get('allowedLocations') or []) and u.get('role') == 'Agent':
        print(f"{u.get('name')} - Role: {u.get('role')} - Shift: {u.get('shiftStart')} to {u.get('shiftEnd')} - Days: {u.get('workingDays')} - Additional: {u.get('additionalShifts')}")
