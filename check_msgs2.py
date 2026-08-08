import sqlite3
from fts_paths import get_data_path
db_path = get_data_path('chat_history.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT * FROM messages WHERE chat_id = 'bb398f15-a128-47ff-9873-53196f7814bc' ORDER BY timestamp DESC LIMIT 5")
for row in c.fetchall():
    print(dict(row))
conn.close()