import sqlite3
from fts_paths import get_data_path
db_path = get_data_path('chat_history.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT sender_identifier, contact_name, source FROM conversations WHERE sender_identifier IN ('01097252642', '201097252642', '37355054830774570')")
for row in c.fetchall():
    print(dict(row))
conn.close()