import sqlite3
import json

db_path = 'chat_history.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("""
    SELECT chat_id, source, booking_number, is_closed, is_deleted, sales_inbox 
    FROM conversations 
    WHERE chat_id IN ('06bb2f42-5086-4b9a-b5f3-9cf36c3b4bd6', 'd28a0b4a-9b11-4996-bbb4-35c023de8c87')
""")
rows = [dict(row) for row in cursor.fetchall()]
print(json.dumps(rows, indent=2))
