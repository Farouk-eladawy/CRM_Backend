# -*- coding: utf-8 -*-
import sqlite3
conn = sqlite3.connect('chat_history.db', timeout=8)
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("""
SELECT text, timestamp, chat_id FROM messages
WHERE text LIKE '%Conversation dismissed by%Reason: Duplicate message%'
ORDER BY timestamp
""")
rows = c.fetchall()
print("Total dismiss log rows:", len(rows))
print("Earliest:", rows[0]['timestamp'], "|", rows[0]['text'][:60])
print("Latest:  ", rows[-1]['timestamp'], "|", rows[-1]['text'][:60])
# count by date
from collections import Counter
cnt = Counter(r['timestamp'][:10] for r in rows)
for d in sorted(cnt):
    print("  ", d, "->", cnt[d])
conn.close()
