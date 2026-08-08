import sqlite3
from fts_paths import get_data_path
db_path = get_data_path('chat_history.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT * FROM conversations WHERE sender_identifier = '27554874670873775'")
row = c.fetchone()
print(dict(row) if row else 'Not found')
conn.close()