# -*- coding: utf-8 -*-
"""
Revert v2 - restore 200 Religious unread targets to pre-operation state.
Removes all bulk-dismiss artifacts (messages + audit) created >= 2026-08-04T20:00 Cairo,
restores conversation fields exactly from the pre-op snapshot.
Preserves legitimate agent dismisses (e.g., Mohamed Barbar "thanks" reasons).
"""
import sqlite3, json
import chat_db

DB = chat_db.DB_FILE
CUTOFF = '2026-08-04T20:00:00'
DISMISS_PAT = '%Conversation dismissed by%Reason: Duplicate message%'

conn = sqlite3.connect(DB, timeout=60.0)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA busy_timeout=60000;")
c = conn.cursor()

# 1) Identify chats dismissed in the bulk window
c.execute("""
SELECT DISTINCT chat_id FROM messages
WHERE text LIKE ? AND timestamp >= ?
""", (DISMISS_PAT, CUTOFF))
dismissed_today = [r['chat_id'] for r in c.fetchall()]
print("Chats with bulk-dismiss logs:", len(dismissed_today))

snap = json.load(open('backups/dismiss_target_snapshot.json', encoding='utf-8'))
snap_map = {t['chat_id']: t for t in snap['targets']}

restored = 0
for chat_id in dismissed_today:
    s = snap_map.get(chat_id)
    if s:
        new_force = s.get('force_read_at')
        new_needs = s.get('needs_help')
        new_unread = s.get('unread_count')
        snap_last = s.get('last_message_time')
    else:
        new_force = None; new_needs = None; new_unread = None; snap_last = None

    c.execute("""
        SELECT MAX(timestamp) AS mx FROM messages
        WHERE chat_id = ?
          AND IFNULL(text,'') NOT LIKE '[PROPOSED_DRAFT]%'
          AND IFNULL(text,'') NOT LIKE ?
    """, (chat_id, DISMISS_PAT))
    row = c.fetchone()
    recomputed_last = row['mx'] if row else None
    if snap_last and recomputed_last:
        new_last = snap_last if snap_last >= recomputed_last else recomputed_last
    else:
        new_last = snap_last or recomputed_last

    sets = ["last_message_time = ?"]
    params = [new_last]
    if s and new_force is None:
        sets.append("force_read_at = NULL")
    elif new_force is not None:
        sets.append("force_read_at = ?"); params.append(new_force)
    if new_needs is not None:
        sets.append("needs_help = ?"); params.append(new_needs)
    if new_unread is not None:
        sets.append("unread_count = ?"); params.append(new_unread)
    params.append(chat_id)
    c.execute(f"UPDATE conversations SET {', '.join(sets)} WHERE chat_id = ?", params)
    restored += 1
print("Conversations restored:", restored)

c.execute("""
DELETE FROM messages
WHERE text LIKE ? AND timestamp >= ?
""", (DISMISS_PAT, CUTOFF))
print("Dismiss messages deleted:", c.rowcount)

c.execute("""
DELETE FROM hr_audit_activity
WHERE event_type = 'dismiss_chat'
  AND created_at >= ?
  AND (meta_json LIKE '%Duplicate message%' OR details_json LIKE '%Duplicate message%')
""", (CUTOFF,))
print("hr_audit dismiss_chat (Duplicate message) deleted:", c.rowcount)

conn.commit()
conn.close()
print("REVERT V2 COMMITTED.")
