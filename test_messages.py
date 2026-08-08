import sqlite3
import json

conn = sqlite3.connect('chat_history.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT * FROM conversations WHERE chat_id = 'd28a0b4a-9b11-4996-bbb4-35c023de8c87'")
row = cursor.fetchone()
print(json.dumps(dict(row), indent=2))
