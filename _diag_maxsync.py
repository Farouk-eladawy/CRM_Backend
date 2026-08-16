import sqlite3, time
con=sqlite3.connect('airtable_mirror.db'); con.row_factory=sqlite3.Row; c=con.cursor()
now=int(time.time())
tk='appTp5YgSp9DV2HYc:tblJodXmOWKiYqiXS'
row=c.execute('SELECT MAX(synced_ts) AS mx, COUNT(*) AS n FROM mirror_records WHERE table_key=?', (tk,)).fetchone()
print('list max synced', dict(row), 'ago', now-int(row['mx'] or 0))
# top 5 newest synced
rows=c.execute('SELECT airtable_id, synced_ts, substr(fields_json,1,120) fj FROM mirror_records WHERE table_key=? ORDER BY synced_ts DESC LIMIT 5', (tk,)).fetchall()
for r in rows:
    d=dict(r); d['ago']=now-int(d['synced_ts'] or 0); print(d)
# any record with synced_ts in last hour
n=c.execute('SELECT COUNT(*) FROM mirror_records WHERE table_key=? AND synced_ts>?', (tk, now-3600)).fetchone()[0]
print('list records synced last hour', n)
con.close()
