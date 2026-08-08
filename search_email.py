import sqlite3

c = sqlite3.connect('chat_history.db')
c.row_factory = sqlite3.Row

rows = c.execute("SELECT * FROM conversations WHERE source='Email' AND (sender_identifier LIKE '%GYGZGZXYNLWF%' OR contact_name LIKE '%BRUNO%')").fetchall()
for r in rows:
    print(dict(r))
