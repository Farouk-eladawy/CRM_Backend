import sqlite3, time, os, json
from pathlib import Path

print("cwd", os.getcwd())
db = Path("airtable_mirror.db")
print("db", db.exists(), db.stat().st_size if db.exists() else 0)
locks = [p.name for p in Path(".").glob("*lock*") if p.is_file()]
pids = [p.name for p in Path(".").glob("*.pid") if p.is_file()]
print("locks", locks, "pids", pids)

con = sqlite3.connect("airtable_mirror.db")
con.row_factory = sqlite3.Row
c = con.cursor()
tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print("tables", tables)
for t in tables:
    if any(x in t.lower() for x in ("sync", "meta", "state")):
        cols = [x[1] for x in c.execute("PRAGMA table_info(%s)" % t)]
        print("TABLE", t, cols)
        for r in c.execute("SELECT * FROM %s" % t).fetchall()[:50]:
            print(dict(r))
for t in tables:
    try:
        print("count", t, c.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0])
    except Exception as e:
        print("countfail", t, e)

now = int(time.time())
print("now", now, time.ctime(now))
try:
    rows = c.execute(
        """
        SELECT t.table_key, t.base_label, t.table_name, t.ignored, t.has_lmt, t.lmt_field,
               t.record_count, t.sync_interval_seconds, s.last_sync_iso, s.last_full_sync_ts, s.next_sync_ts
        FROM mirror_tables t
        LEFT JOIN mirror_sync_state s ON s.table_key=t.table_key
        WHERE t.table_name='List' OR t.table_key LIKE '%List%' OR t.base_label='main'
        ORDER BY t.base_label, t.table_name
        """
    ).fetchall()
    print("MAIN_OR_LIST")
    for r in rows:
        d = dict(r)
        ns = d.get("next_sync_ts")
        d["overdue_sec"] = (now - int(ns)) if ns is not None else None
        print(d)
except Exception as e:
    print("joinfail", e)

try:
    for r in c.execute("SELECT table_key,last_sync_iso,last_full_sync_ts,next_sync_ts FROM mirror_sync_state").fetchall():
        d = dict(r)
        ns = d.get("next_sync_ts")
        d["overdue_sec"] = (now - int(ns)) if ns is not None else None
        if d["overdue_sec"] is not None and d["overdue_sec"] > 60:
            print("OVERDUE", d)
except Exception as e:
    print("statefail", e)

# booking search in projection / records
for t in tables:
    cols = [x[1] for x in c.execute("PRAGMA table_info(%s)" % t)]
    useful = [col for col in cols if any(x in col.lower() for x in ("booking", "nr", "fields", "json", "payload", "record"))]
    if not useful:
        continue
    where = " OR ".join(["CAST(%s AS TEXT) LIKE '%%33416130%%'" % col for col in useful[:8]])
    try:
        rows = c.execute("SELECT * FROM %s WHERE %s LIMIT 3" % (t, where)).fetchall()
        if rows:
            print("HIT", t)
            for r in rows:
                d = {k: (str(v)[:240] if v is not None else None) for k, v in dict(r).items()}
                print(d)
    except Exception as e:
        print("searchfail", t, e)

# meta
try:
    for r in c.execute("SELECT * FROM mirror_meta").fetchall():
        print("META", dict(r))
except Exception as e:
    print("metafail", e)

con.close()
print("done_db")
