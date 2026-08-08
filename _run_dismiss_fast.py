# -*- coding: utf-8 -*-
"""
Bulk Dismiss (Duplicate message) - FAST SINGLE-CONNECTION VERSION
Scope: Religious, unread (is_unread_computed=1 OR needs_help=1), last_message_time < 2026-08-03
Replicates exactly the UI Confirm Dismiss flow:
  1) insert "[System Log] Conversation dismissed by {actor}. Reason: Duplicate message"
  2) needs_help = 0
  3) force_read_at = now (Cairo time)
  4) HR audit entry event_type='dismiss_chat'
"""
import json, sqlite3, uuid, sys, time
import chat_db

ACTOR_ID = "15"; ACTOR_NAME = "Mohamed Sami"; ACTOR_ROLE = "Admin"
REASON = "Duplicate message"

snap = json.load(open('backups/dismiss_target_snapshot_v2.json', encoding='utf-8'))
targets = snap['targets']
print(f"Targets: {len(targets)}", flush=True)

now = chat_db.get_cairo_time()
log_text = f"[System Log] Conversation dismissed by {ACTOR_NAME}. Reason: {REASON}"

conn = sqlite3.connect(chat_db.DB_FILE, timeout=60.0)
try:
    conn.execute("PRAGMA busy_timeout=60000;")
except Exception:
    pass
cur = conn.cursor()

ok = 0
fail = []
t0 = time.time()

for i, t in enumerate(targets, 1):
    chat_id = t['chat_id']
    try:
        # 1) system log message (same fields add_message uses)
        msg_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO messages (msg_id, chat_id, sender_type, text, timestamp, status, source, external_message_id, reaction_to_external_message_id, reaction_emoji) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (msg_id, chat_id, 'agent', log_text, now, 'sent', None, None, None, None)
        )
        # add_message also bumps last_message_time for non-draft text
        cur.execute("UPDATE conversations SET last_message_time = ? WHERE chat_id = ?", (now, chat_id))
        # 2) needs_help = False
        cur.execute("UPDATE conversations SET needs_help = 0 WHERE chat_id = ?", (chat_id,))
        # 3) force_read_at = now
        cur.execute("UPDATE conversations SET force_read_at = ? WHERE chat_id = ?", (now, chat_id))
        # 4) HR audit entry
        meta_json = json.dumps({"chat_id": chat_id, "reason": REASON}, ensure_ascii=False)
        details_json = json.dumps({"description": "Conversation dismissed", "meta": {"chat_id": chat_id, "reason": REASON}}, ensure_ascii=False)
        cur.execute(
            "INSERT INTO hr_audit_activity (actor_user_id, actor_name, actor_role, event_type, meta_json, details_json, details_enc, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (ACTOR_ID, ACTOR_NAME, ACTOR_ROLE, "dismiss_chat", meta_json, details_json, None, now)
        )
        ok += 1
        if i % 25 == 0:
            conn.commit()  # release lock periodically
            print(f"  ...{i}/{len(targets)} ok", flush=True)
    except Exception as e:
        fail.append({"chat_id": chat_id, "error": str(e)})
        print(f"[FAIL] {chat_id}: {e}", flush=True)

conn.commit()
conn.close()
elapsed = time.time() - t0
print(f"DONE in {elapsed:.1f}s | ok={ok} fail={len(fail)}", flush=True)

with open('backups/dismiss_execution_result.json', 'w', encoding='utf-8') as f:
    json.dump({"executed_at": now, "actor": ACTOR_NAME, "actor_id": ACTOR_ID, "reason": REASON,
               "elapsed_sec": round(elapsed, 1), "ok": ok, "fail": fail}, f, ensure_ascii=False, indent=1)
print("Result saved -> backups/dismiss_execution_result.json", flush=True)
