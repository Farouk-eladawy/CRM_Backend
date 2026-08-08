# -*- coding: utf-8 -*-
import json
import sqlite3
from pathlib import Path

try:
    from fts_paths import get_data_path
    db = Path(get_data_path("chat_history.db"))
except Exception:
    db = Path("chat_history.db")

RECS = ["recwKBwCxP3FuCBDV", "recgnTNmJcc7SWm9x"]
conn = sqlite3.connect(str(db))
conn.row_factory = sqlite3.Row
c = conn.cursor()

out = {"db": str(db), "chats": []}
for rec in RECS:
    c.execute(
        """
        SELECT chat_id, contact_name, location, source, sender_identifier,
               airtable_record_id, last_message_time, unread_count, force_read_at,
               needs_help, facebook_ad_id, facebook_ad_title, lead_owner_name
        FROM conversations
        WHERE airtable_record_id = ?
        ORDER BY last_message_time DESC
        LIMIT 3
        """,
        (rec,),
    )
    convs = [dict(r) for r in c.fetchall()]
    for conv in convs:
        cid = conv["chat_id"]
        c.execute(
            """
            SELECT sender_type, substr(text,1,160) AS text, timestamp, status, source
            FROM messages
            WHERE chat_id = ?
            ORDER BY timestamp DESC, rowid DESC
            LIMIT 12
            """,
            (cid,),
        )
        msgs = [dict(r) for r in c.fetchall()]
        drafts = sum(1 for m in msgs if str(m.get("text") or "").startswith("[PROPOSED_DRAFT]"))
        # recompute unread like chat_db
        c.execute(
            """
            SELECT
              CASE
                WHEN m2.sender_type = 'customer' AND m2.text LIKE '%[Customer reacted%' THEN 0
                WHEN m2.sender_type = 'customer' AND m2.text LIKE '[Facebook Ad Referral]%' THEN 0
                WHEN m2.sender_type = 'customer' AND m2.text LIKE '[Facebook Referral]%' THEN 0
                WHEN m2.sender_type = 'customer' THEN 1
                WHEN m2.text LIKE '%تم سحب المحادثة%' THEN 1
                ELSE 0
              END AS is_unread_computed
            FROM messages m2
            WHERE m2.chat_id = ?
              AND ( ? IS NULL OR m2.timestamp > ? )
              AND IFNULL(m2.text, '') NOT LIKE '[PROPOSED_DRAFT]%'
            ORDER BY m2.timestamp DESC
            LIMIT 1
            """,
            (cid, conv.get("force_read_at"), conv.get("force_read_at")),
        )
        ur = c.fetchone()
        out["chats"].append({
            "record": rec,
            "conv": conv,
            "drafts_in_last12": drafts,
            "is_unread_computed": (ur["is_unread_computed"] if ur else 0),
            "last_msgs": msgs,
        })

Path("_inspect_two_chats_out.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2, default=str),
    encoding="utf-8",
)
print("WROTE _inspect_two_chats_out.json")
