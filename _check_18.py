# -*- coding: utf-8 -*-
import sqlite3, json

# What did the post-dismiss backup (10:31) contain?
bak = sqlite3.connect('backups/chat_history.POST_dismiss_before_revert_20260804-103118.db')
bak.row_factory = sqlite3.Row
c = bak.cursor()
c.execute("""
SELECT COUNT(*) AS cnt FROM messages
WHERE text LIKE '%Conversation dismissed by%Reason: Duplicate message%'
  AND timestamp >= '2026-08-04T20:00:00'
""")
print("Post-dismiss backup: dismiss msgs >= 20:00:", c.fetchone()['cnt'])
c.execute("""
SELECT COUNT(*) AS cnt FROM messages
WHERE text LIKE '%Conversation dismissed by%Reason: Duplicate message%'
  AND timestamp >= '2026-08-04T00:00:00'
""")
print("Post-dismiss backup: dismiss msgs all today:", c.fetchone()['cnt'])
bak.close()

# Current state of my 200 targets
conn = sqlite3.connect('chat_history.db', timeout=8)
conn.row_factory = sqlite3.Row
c = conn.cursor()
snap = json.load(open('backups/dismiss_target_snapshot.json', encoding='utf-8'))
snap_map = {t['chat_id']: t for t in snap['targets']}
ids = list(snap_map.keys())
ph = ",".join(["?"] * len(ids))
c.execute(f"""
SELECT chat_id, last_message_time, force_read_at, needs_help, unread_count
FROM conversations WHERE chat_id IN ({ph})
""", ids)
still = []
for r in c.fetchall():
    if r['force_read_at'] is not None:
        still.append(dict(r))
print("\nMy 200 targets with force_read_at NOT NULL now:", len(still))
for s in still[:18]:
    print("  ", s['chat_id'][:8], "| force_read:", s['force_read_at'], "| last_msg:", s['last_message_time'])
conn.close()
