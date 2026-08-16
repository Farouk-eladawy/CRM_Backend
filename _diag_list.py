import sqlite3, time, json, os
from pathlib import Path

con = sqlite3.connect("airtable_mirror.db")
con.row_factory = sqlite3.Row
c = con.cursor()
now = int(time.time())
print("now", now, time.ctime(now))

rows = c.execute(
    """
    SELECT t.table_key, t.base_label, t.table_name, t.has_lmt, t.lmt_field, t.record_count,
           t.sync_interval_seconds, s.last_sync_iso, s.last_full_sync_ts, s.next_sync_ts
    FROM mirror_tables t
    LEFT JOIN mirror_sync_state s ON s.table_key=t.table_key
    WHERE t.table_name='List' AND t.base_label='main'
    """
).fetchall()
print("LIST_MAIN")
for r in rows:
    d = dict(r)
    ns = d.get("next_sync_ts")
    d["overdue_sec"] = (now - int(ns)) if ns is not None else None
    d["last_full_ago"] = (now - int(d["last_full_sync_ts"])) if d.get("last_full_sync_ts") else None
    print(d)

# booking in projection
rows = c.execute(
    "SELECT * FROM mirror_list_projection WHERE booking_nr LIKE '%33416130%' LIMIT 5"
).fetchall()
print("PROJ_HITS", len(rows))
for r in rows:
    print({k: dict(r)[k] for k in dict(r)})

# also fields_json search limited
tk = rows[0]["airtable_id"] if rows else None
if not rows:
    # try mirror_records via join table key
    list_key = c.execute("SELECT table_key FROM mirror_tables WHERE base_label='main' AND table_name='List'").fetchone()
    print("list_key", dict(list_key) if list_key else None)
    if list_key:
        q = c.execute(
            "SELECT airtable_id, substr(fields_json,1,500) AS fj FROM mirror_records WHERE table_key=? AND fields_json LIKE '%33416130%' LIMIT 3",
            (list_key[0],),
        ).fetchall()
        print("REC_HITS", len(q))
        for r in q:
            print(dict(r))
else:
    print("booking present in local mirror projection")

for r in c.execute("SELECT * FROM mirror_meta").fetchall():
    d = dict(r)
    if d["key"].endswith("_ts"):
        try:
            v = int(d["value"]); print("META", d["key"], v, "ago", now-v, time.ctime(v))
        except Exception:
            print("META", d)
    else:
        print("META", d)

con.close()
