import sqlite3
import json

db_name = 'chat_history.db'
print(f"--- Schema for {db_name} ---")
conn = sqlite3.connect(db_name)
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print('Tables:', tables)
for table in tables:
    t = table[0]
    c.execute(f"PRAGMA table_info({t})")
    print(f'Schema for {t}:', c.fetchall())

db_name = 'chat_db.db'
print(f"\n--- Schema for {db_name} ---")
conn = sqlite3.connect(db_name)
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print('Tables:', tables)
for table in tables:
    t = table[0]
    c.execute(f"PRAGMA table_info({t})")
    print(f'Schema for {t}:', c.fetchall())

print("\n--- Try fetching user settings from chat_db.db ---")
try:
    c.execute("SELECT setting_value FROM user_settings WHERE setting_key = ?", ('internal_assistant_session:201010323484',))
    row = c.fetchone()
    if row:
        print(json.dumps(json.loads(row[0]), indent=2, ensure_ascii=False))
except Exception as e:
    print(e)
