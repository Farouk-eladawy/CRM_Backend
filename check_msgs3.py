import sqlite3
from fts_paths import get_data_path
db_path = get_data_path('chat_history.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT * FROM messages WHERE timestamp LIKE '2026-07-19T17:56%' OR timestamp LIKE '2026-07-19T17:55%' ORDER BY timestamp ASC")
for row in c.fetchall():
    print(dict(row))
conn.close()