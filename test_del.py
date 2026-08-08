import sqlite3
c = sqlite3.connect('chat_history.db')
c.row_factory = sqlite3.Row
r = c.execute("SELECT is_deleted FROM conversations WHERE booking_number = 'GYGWZAR7W72F'").fetchone()
print(dict(r))
