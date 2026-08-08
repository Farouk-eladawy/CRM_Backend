# -*- coding: utf-8 -*-
import sqlite3, json

# 1) v2 snapshot targets (other session)
try:
    snap = json.load(open('backups/dismiss_target_snapshot_v2.json', encoding='utf-8'))
    t2 = snap['targets']
    print("v2 snapshot targets:", len(t2))
    dates2 = sorted({str(t.get('last_message_time',''))[:10] for t in t2})
    print("v2 target date range sample (first 8):", t2[:2])
    # compare with my snapshot
    mine = json.load(open('backups/dismiss_target_snapshot.json', encoding='utf-8'))['targets']
    my_ids = {t['chat_id'] for t in mine}
    v2_ids = {t['chat_id'] for t in t2}
    print("overlap mine-v2:", len(my_ids & v2_ids), "| only in v2:", len(v2_ids - my_ids), "| only mine:", len(my_ids - v2_ids))
except Exception as e:
    print("v2 err:", e)

# 2) Latest force_read_at pattern on dismissed chats - check if dismiss timestamps used UTC (17:xx)
conn = sqlite3.connect('chat_history.db', timeout=8)
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("""
SELECT DISTINCT chat_id FROM messages
WHERE text LIKE '%Conversation dismissed by%Reason: Duplicate message%'
""")
dismissed = [r['chat_id'] for r in c.fetchall()]
ph = ",".join(["?"] * len(dismissed))
c.execute(f"SELECT chat_id, force_read_at, needs_help FROM conversations WHERE chat_id IN ({ph})", dismissed)
rows = c.fetchall()
utc_pattern = [r for r in rows if r['force_read_at'] and 'T1' in r['force_read_at'] or (r['force_read_at'] and r['force_read_at'][11:13] in ('17','16','18'))]
print("\nDismissed chats (sample 12):")
for r in rows[:12]:
    print(" ", r['chat_id'][:8], "force_read:", r['force_read_at'], "needs_help:", r['needs_help'])
conn.close()
