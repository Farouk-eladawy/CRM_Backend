import sqlite3
from fts_paths import get_data_path
db_path = get_data_path('chat_history.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT * FROM messages WHERE chat_id = '24785d0c-b653-4871-b84d-743ef428cd25' ORDER BY timestamp DESC LIMIT 5")
for row in c.fetchall():
    print(dict(row))
conn.close()