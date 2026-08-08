# -*- coding: utf-8 -*-
"""
FINAL Bulk Dismiss (Duplicate message) - Religious, unread, before 2026-08-03
- Recomputes targets fresh (skips chats already dismissed after 2026-08-03)
- Single connection, per-chat transaction, busy_timeout=60s
- Replicates UI Confirm Dismiss: system log msg + needs_help=0 + force_read_at + HR audit
"""
import json, sqlite3, uuid, time
import chat_db

ACTOR_ID = "1"; ACTOR_NAME = "Admin Manager"; ACTOR_ROLE = "Admin"
REASON = "Duplicate message"

conn = sqlite3.connect(chat_db.DB_FILE, timeout=60.0)
conn.execute("PRAGMA busy_timeout=60000;")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# ---------- Step A: fresh target recompute ----------
rows = cur.execute("""
WITH conv AS (
  SELECT chat_id, force_read_at, location, last_message_time, needs_help, airtable_record_id
  FROM conversations
  WHERE location = 'Religious' AND COALESCE(is_deleted,0) = 0
),
unread_msg AS (
  SELECT m2.chat_id,
    CASE
      WHEN m2.sender_type = 'customer' AND m2.text LIKE '%[Customer reacted%' THEN 0
      WHEN m2.sender_type = 'customer' THEN 1
      WHEN m2.text LIKE '%تم سحب المحادثة%' THEN 1
      ELSE 0 END AS is_unread_computed,
    ROW_NUMBER() OVER (PARTITION BY m2.chat_id ORDER BY m2.timestamp DESC) AS rn
  FROM messages m2 JOIN conv c2 ON c2.chat_id = m2.chat_id
  WHERE (c2.force_read_at IS NULL OR m2.timestamp > c2.force_read_at)
    AND IFNULL(m2.text,'') NOT LIKE '[PROPOSED_DRAFT]%'
),
unread_one AS (SELECT chat_id, is_unread_computed FROM unread_msg WHERE rn=1)
SELECT conv.chat_id, conv.needs_help, conv.last_message_time,
       COALESCE(uo.is_unread_computed,0) AS is_unread_computed
FROM conv LEFT JOIN unread_one uo ON uo.chat_id = conv.chat_id
WHERE conv.last_message_time < '2026-08-03'
""").fetchall()
targets = [dict(r) for r in rows if (dict(r)['is_unread_computed'] == 1 or dict(r)['needs_help'] == 1)]
print(f"Fresh targets (Religious, unread/needs_help, before 2026-08-03): {len(targets)}", flush=True)

# ---------- Step B: filter out already-dismissed (skip double-processing) ----------
pending = []
for t in targets:
    cid = t['chat_id']
    already = cur.execute(
        """SELECT 1 FROM messages
           WHERE chat_id = ? AND text LIKE '%Conversation dismissed by%Duplicate message%'
             AND timestamp > '2026-08-03' LIMIT 1""",
        (cid,),
    ).fetchone()
    if not already:
        pending.append(t)
print(f"Pending (not yet dismissed): {len(pending)}", flush=True)

# ---------- Step C: execute dismiss ----------
now = chat_db.get_cairo_time()
log_text = f"[System Log] Conversation dismissed by {ACTOR_NAME}. Reason: {REASON}"
ok, fail = [], []
t0 = time.time()

for i, t in enumerate(pending, 1):
    cid = t['chat_id']
    try:
        cur.execute("BEGIN IMMEDIATE")
        # 1) system log message (same fields as chat_db.add_message for agent/system)
        cur.execute(
            """INSERT INTO messages (msg_id, chat_id, sender_type, text, timestamp, status)
               VALUES (?, ?, 'agent', ?, ?, 'sent')""",
            (str(uuid.uuid4()), cid, log_text, now),
        )
        # update conversation last_message_time exactly like add_message does
        cur.execute("UPDATE conversations SET last_message_time = ? WHERE chat_id = ?", (now, cid))
        # 2) needs_help = 0
        cur.execute("UPDATE conversations SET needs_help = 0 WHERE chat_id = ?", (cid,))
        # 3) force_read_at = now (Cairo)
        cur.execute("UPDATE conversations SET force_read_at = ? WHERE chat_id = ?", (now, cid))
        # 4) HR audit entry
        chat_db.log_hr_audit_activity(
            actor_user_id=ACTOR_ID, actor_name=ACTOR_NAME, actor_role=ACTOR_ROLE,
            event_type="dismiss_chat", description="Conversation dismissed",
            meta={"chat_id": cid, "reason": REASON},
        )
        cur.execute("COMMIT")
        ok.append(cid)
        if i % 25 == 0:
            print(f"  ...{i}/{len(pending)} done ({time.time()-t0:.1f}s)", flush=True)
    except Exception as e:
        try:
            cur.execute("ROLLBACK")
        except Exception:
            pass
        fail.append({"chat_id": cid, "error": str(e)})
        print(f"[FAIL] {cid}: {e}", flush=True)

conn.close()
print(f"\nDone. Success: {len(ok)} | Failed: {len(fail)}", flush=True)

with open('backups/dismiss_execution_result.json', 'w', encoding='utf-8') as f:
    json.dump({"executed_at": now, "actor": ACTOR_NAME, "actor_id": ACTOR_ID, "reason": REASON,
               "success": ok, "failed": fail}, f, ensure_ascii=False, indent=1)
print("Result -> backups/dismiss_execution_result.json", flush=True)
