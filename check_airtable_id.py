import sqlite3
import json

conn = sqlite3.connect('chat_history.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT chat_id, airtable_record_id, source FROM conversations WHERE chat_id IN ('06bb2f42-5086-4b9a-b5f3-9cf36c3b4bd6', 'd28a0b4a-9b11-4996-bbb4-35c023de8c87')")
print(json.dumps([dict(r) for r in cursor.fetchall()], indent=2))
