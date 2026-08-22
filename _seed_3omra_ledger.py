# -*- coding: utf-8 -*-
from workflows.send_3omra_campaign import _seed_sent_from_chat_history, _connect_sent_db

_seed_sent_from_chat_history()
with _connect_sent_db() as conn:
    rows = conn.execute("SELECT status, COUNT(*) FROM sent_phones GROUP BY status").fetchall()
print("ledger seeded", dict(rows))
