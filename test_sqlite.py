import sqlite3
conn = sqlite3.connect(':memory:')
c = conn.cursor()
c.execute("SELECT '2026-07-30T14:00:00.123456' < '2026-07-30 15:00:00'")
print('Result:', c.fetchone()[0])
