import sqlite3
conn = sqlite3.connect('knowledge.db')
conn.execute('PRAGMA writable_schema = ON')
conn.execute("DELETE FROM sqlite_master WHERE name LIKE 'trips_fts%'")
conn.execute('PRAGMA writable_schema = OFF')
conn.commit()
print("Cleaned up corrupted trips_fts table completely.")
