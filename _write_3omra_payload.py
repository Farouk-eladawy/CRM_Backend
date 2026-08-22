# -*- coding: utf-8 -*-
import json
import sqlite3
import chat_db
from workflows.send_3omra_campaign import TARGET_PHONES, _clean_phone, _dedupe, SENT_DB

phones = _dedupe(TARGET_PHONES)
sent = set()
with sqlite3.connect(SENT_DB, timeout=30.0) as conn:
    for (p,) in conn.execute("SELECT phone FROM sent_phones WHERE status IN ('sent','sending','uncertain')"):
        sent.add(_clean_phone(p))
with sqlite3.connect(chat_db.DB_FILE, timeout=30.0) as conn:
    conn.execute("PRAGMA busy_timeout=30000")
    for (ident,) in conn.execute(
        """
        SELECT DISTINCT c.sender_identifier
        FROM messages m
        JOIN conversations c ON c.chat_id = m.chat_id
        WHERE IFNULL(m.text, '') LIKE '[Campaign 3omra]%'
          AND IFNULL(m.text, '') NOT LIKE '%FAILED%'
          AND IFNULL(m.status, '') != 'error'
        """
    ):
        sent.add(_clean_phone(ident or ""))

remaining = [p for p in phones if p not in sent]
payload = {
    "script_name": "send_3omra_campaign.py",
    "payload": {
        "phones": remaining,
        "dry_run": False,
        "force": False,
        "delay_sec": 2.5,
    },
}
with open("_3omra_remaining_payload.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False)
print("remaining", len(remaining))
print("payload_written")
