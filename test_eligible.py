import json
import sqlite3
from datetime import datetime

users_raw = """[{"id": "1783096103617", "username": "Hanady", "name": "هنادي محمد", "role": "Agent", "allowedLocations": ["Religious"], "workingDays": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"], "shiftStart": "04:00", "shiftEnd": "10:00", "additionalShifts": [{"start": "18:00", "end": "23:00"}]}, {"id": "17", "username": "Ahmed", "name": "أحمد خليل", "role": "Agent", "allowedLocations": ["Religious"], "workingDays": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"], "shiftStart": "10:00", "shiftEnd": "18:00", "additionalShifts": [{"start": "23:00", "end": "04:00"}]}]"""

users = json.loads(users_raw)
current_day = 'Thursday'
current_time = '18:09'

def is_time_in_shift(curr, start, end):
    if not start or not end:
        return False
    if start <= end:
        return start <= curr <= end
    else:
        return curr >= start or curr <= end

eligible_agents = []
for u in users:
    if 'Religious' in (u.get('allowedLocations') or []) and u.get('role') == 'Agent':        
        working_days = u.get('workingDays') or ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        shift_start = u.get('shiftStart') or "00:00"
        shift_end = u.get('shiftEnd') or "23:59"
        additional_shifts = u.get('additionalShifts') or []

        if current_day in working_days:
            is_in_shift = False
            if is_time_in_shift(current_time, shift_start, shift_end):
                is_in_shift = True
            else:
                for shift in additional_shifts:
                    if shift.get('start') and shift.get('end'):
                        if is_time_in_shift(current_time, shift['start'], shift['end']):     
                            is_in_shift = True
                            break
            if is_in_shift:
                eligible_agents.append(u)

print("Eligible agents at 18:09:", [a['name'] for a in eligible_agents])
