import sqlite3, time, json, urllib.request
con=sqlite3.connect('airtable_mirror.db'); con.row_factory=sqlite3.Row; c=con.cursor()
tk='appTp5YgSp9DV2HYc:tblJodXmOWKiYqiXS'
now=int(time.time())
mx1=c.execute('SELECT MAX(synced_ts) FROM mirror_records WHERE table_key=?',(tk,)).fetchone()[0]
n1=c.execute('SELECT COUNT(*) FROM mirror_records WHERE table_key=? AND synced_ts>?',(tk, now-120)).fetchone()[0]
print('t0', now, 'max', mx1, 'synced_last_2min', n1)
time.sleep(8)
now2=int(time.time())
mx2=c.execute('SELECT MAX(synced_ts) FROM mirror_records WHERE table_key=?',(tk,)).fetchone()[0]
n2=c.execute('SELECT COUNT(*) FROM mirror_records WHERE table_key=? AND synced_ts>?',(tk, now2-120)).fetchone()[0]
print('t1', now2, 'max', mx2, 'synced_last_2min', n2, 'max_delta', mx2-mx1)
hit=c.execute("SELECT airtable_id, booking_nr, last_modified_iso FROM mirror_list_projection WHERE booking_nr='33416130'").fetchall()
print('proj', [dict(r) for r in hit])
hit2=c.execute("SELECT airtable_id FROM mirror_records WHERE table_key=? AND fields_json LIKE '%33416130%' LIMIT 3",(tk,)).fetchall()
print('recs', [dict(r) for r in hit2])
st=c.execute("SELECT * FROM mirror_sync_state WHERE table_key=?",(tk,)).fetchone()
print('state', dict(st), 'overdue', now2-int(dict(st)['next_sync_ts']))
# distinct synced_ts buckets last 10 min
rows=c.execute('SELECT synced_ts, COUNT(*) c FROM mirror_records WHERE table_key=? AND synced_ts>? GROUP BY synced_ts ORDER BY synced_ts DESC LIMIT 15',(tk, now2-600)).fetchall()
print('recent_buckets')
for r in rows:
    print(dict(r))
con.close()
