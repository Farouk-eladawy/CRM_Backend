import json, urllib.request, time
now=int(time.time())
print('now', now, time.ctime(now))
with urllib.request.urlopen('https://api.ftstravels.com/api/mirror/status', timeout=30) as resp:
    data=json.loads(resp.read().decode())
rows=data.get('data') or data
list_rows=[r for r in rows if r.get('table_name')=='List' and r.get('base_label')=='main']
print('LIST', list_rows)
overdue=[r for r in rows if r.get('next_sync_ts') and now-int(r['next_sync_ts'])>60]
print('tables', len(rows), 'overdue60', len(overdue))
# newest next_sync among all
ns=max(int(r['next_sync_ts']) for r in rows if r.get('next_sync_ts'))
ls=[r.get('last_sync_iso') for r in rows if r.get('last_sync_iso')]
print('max_next_sync', ns, 'ago', now-ns, time.ctime(ns))
print('sample last_sync_iso newest', sorted([x for x in ls if x])[-5:])
with urllib.request.urlopen('https://api.ftstravels.com/api/operations/mirror_version', timeout=20) as resp:
    print('version', resp.read().decode()[:500])
