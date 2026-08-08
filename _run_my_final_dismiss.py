# -*- coding: utf-8 -*-
"""
Bulk Dismiss (Duplicate message) - FINAL, SINGLE-CONNECTION, IDEMPOTENT
Scope: Religious ONLY, Unread-tab (is_unread_computed=1 OR needs_help=1),
       last_message_time < 2026-08-03 (Cairo).
Replicates UI Confirm Dismiss: system log msg + needs_help=0 + force_read_at + HR audit.
Audit rows inserted on the SAME connection/transaction (no cross-connection deadlock).
"""
import json, sqlite3, uuid, time
import chat_db

ACTOR_ID = "1"; ACTOR_NAME = "Admin Manager"; ACTOR_ROLE = "Admin"
REASON = "Duplicate message"

conn = sqlite3.connect(chat_db.DB_FILE, timeout=60.0)
conn.execute("PRAGMA busy_timeout=20000;")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# ---------- Step A: fresh target recompute ----------
rows = cur.execute("""
WITH conv AS (
  SELECT chat_id, force_read_at, location, last_message_time, needs_help
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
print(f"Fresh targets: {len(targets)}", flush=True)

# ---------- Step B: skip already-dismissed ----------
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
print(f"Pending: {len(pending)}", flush=True)

now = chat_db.get_cairo_time()
log_text = f"[System Log] Conversation dismissed by {ACTOR_NAME}. Reason: {REASON}"
ok, fail = [], []
t0 = time.time()

for i, t in enumerate(pending, 1):
    cid = t['chat_id']
    try:
        cur.execute("BEGIN IMMEDIATE")
        # 1) system log message
        cur.execute(
            "INSERT INTO messages (msg_id, chat_id, sender_type, text, timestamp, status) VALUES (?,?,'agent',?,?,'sent')",
            (str(uuid.uuid4()), cid, log_text, now),
        )
        # 2) conversation updates (same as add_message + dismiss endpoint)
        cur.execute("UPDATE conversations SET last_message_time = ? WHERE chat_id = ?", (now, cid))
        cur.execute("UPDATE conversations SET needs_help = 0 WHERE chat_id = ?", (cid,))
        cur.execute("UPDATE conversations SET force_read_at = ? WHERE chat_id = ?", (now, cid))
        # 3) HR audit row (same connection)
        meta_json = json.dumps({"chat_id": cid, "reason": REASON}, ensure_ascii=False)
        details_json = json.dumps({"description": "Conversation dismissed", "meta": {"chat_id": cid, "reason": REASON}}, ensure_ascii=False)
        cur.execute(
            "INSERT INTO hr_audit_activity (actor_user_id, actor_name, actor_role, event_type, meta_json, details_json, details_enc, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (ACTOR_ID, ACTOR_NAME, ACTOR_ROLE, "dismiss_chat", meta_json, details_json, None, now),
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

with open('backups/my_dismiss_execution_result.json', 'w', encoding='utf-8') as f:
    json.dump({"executed_at": now, "actor": ACTOR_NAME, "actor_id": ACTOR_ID, "reason": REASON,
               "targets": len(targets), "success": ok, "failed": fail}, f, ensure_ascii=False, indent=1)
print("Result -> backups/my_dismiss_execution_result.json", flush=True)
