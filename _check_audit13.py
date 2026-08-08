# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('chat_history.db', timeout=8)
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("""
SELECT actor_user_id, actor_name, actor_role, event_type, created_at, meta_json, details_json
FROM hr_audit_activity
WHERE event_type='dismiss_chat' AND created_at >= '2026-08-04T20:00:00'
ORDER BY created_at
""")
for r in c.fetchall():
    print(r['created_at'], "|", r['actor_name'], "|", str(r['meta_json'])[:120])
conn.close()
