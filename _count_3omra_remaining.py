# -*- coding: utf-8 -*-
import os
import sqlite3
from collections import Counter

import chat_db
from workflows.send_3omra_campaign import TARGET_PHONES, _clean_phone, _dedupe, SENT_DB

phones = _dedupe(TARGET_PHONES)
print("TARGET unique", len(phones))
print("SENT_DB", SENT_DB, "exists", os.path.exists(SENT_DB))
print("CHAT_DB", chat_db.DB_FILE, "exists", os.path.exists(chat_db.DB_FILE))

sent_from_chat = set()
with sqlite3.connect(chat_db.DB_FILE, timeout=30.0) as conn:
    conn.execute("PRAGMA busy_timeout=30000")
    rows = conn.execute(
        """
        SELECT DISTINCT c.sender_identifier
        FROM messages m
        JOIN conversations c ON c.chat_id = m.chat_id
        WHERE IFNULL(m.text, '') LIKE '[Campaign 3omra]%'
          AND IFNULL(m.text, '') NOT LIKE '%FAILED%'
          AND IFNULL(m.status, '') != 'error'
        """
    ).fetchall()
    for r in rows:
        p = _clean_phone(r[0] or "")
        if p:
            sent_from_chat.add(p)
print("sent_from_chat", len(sent_from_chat))

ledger = {}
if os.path.exists(SENT_DB):
    with sqlite3.connect(SENT_DB, timeout=30.0) as conn:
        for phone, status, claimed_at, sent_at, error in conn.execute(
            "SELECT phone, status, claimed_at, sent_at, error FROM sent_phones"
        ):
            ledger[_clean_phone(phone)] = (status, claimed_at, sent_at, error)
print("ledger rows", len(ledger))
print("ledger statuses", dict(Counter(v[0] for v in ledger.values())) if ledger else {})

already = set()
for p in phones:
    if p in sent_from_chat:
        already.add(p)
    st = (ledger.get(p) or ("",))[0]
    if st in ("sent", "sending", "uncertain"):
        already.add(p)

remaining = [p for p in phones if p not in already]
failed = [p for p in phones if (ledger.get(p) or ("",))[0] == "failed"]
sending_stuck = [p for p in phones if (ledger.get(p) or ("",))[0] == "sending" and p not in sent_from_chat]
print("already treated as sent", len(already))
print("remaining never sent", len(remaining))
print("failed in ledger", len(failed))
print("stuck sending without chat log", len(sending_stuck))
print("REMAINING_JSON_START")
import json
print(json.dumps(remaining, ensure_ascii=False))
print("REMAINING_JSON_END")
