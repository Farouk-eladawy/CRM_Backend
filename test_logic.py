import json
import sqlite3
from datetime import datetime

with sqlite3.connect('chat_history.db') as conn:
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT value FROM user_settings WHERE key='dashboard_users'")
    row = c.fetchone()
    users = json.loads(row['value']) if row else []
    
    c.execute("SELECT value FROM user_settings WHERE key='last_assigned_religious_agent'")
    row = c.fetchone()
    last_assigned = row['value'] if row else ""
    
now = datetime.now()
current_day = now.strftime('%A')
current_time = now.strftime('%H:%M')

print("Current:", current_day, current_time)

eligible_agents = []
for u in users:
    if 'Religious' in (u.get('allowedLocations') or []):
        working_days = u.get('workingDays') or []
        shift_start = u.get('shiftStart') or ""
        shift_end = u.get('shiftEnd') or ""
        print("Checking", u.get('username'), "shifts:", shift_start, "to", shift_end, "days:", working_days)
        if current_day in working_days and shift_start and shift_end:
            if shift_start <= current_time <= shift_end:
                eligible_agents.append(u)

print("Eligible:", [u.get('username') for u in eligible_agents])
print("Last assigned:", last_assigned)

if eligible_agents:
    eligible_agents.sort(key=lambda x: str(x.get('id')))
    next_agent = None
    if not last_assigned:
        next_agent = eligible_agents[0]
    else:
        for i, agent in enumerate(eligible_agents):
            if str(agent.get('id')) == last_assigned:
                next_agent = eligible_agents[(i + 1) % len(eligible_agents)]
                break
        if not next_agent:
            next_agent = eligible_agents[0]
            
    print("Next assigned:", next_agent.get('username'))
