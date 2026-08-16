import json, urllib.request, urllib.error
# GET-only safe probes
for url in [
    'https://api.ftstravels.com/api/mirror/status',
    'https://api.ftstravels.com/api/operations/mirror_version',
]:
    try:
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = resp.read().decode('utf-8', 'replace')
            print('OK', url, resp.status)
            # summarize if json
            try:
                data = json.loads(body)
                if isinstance(data, list):
                    list_rows = [r for r in data if str(r.get('table_name'))=='List' and str(r.get('base_label'))=='main']
                    print('list_rows', list_rows[:2])
                    # overdue summary
                    import time
                    now=int(time.time())
                    overdue=[r for r in data if r.get('next_sync_ts') and now-int(r['next_sync_ts'])>60]
                    print('tables', len(data), 'overdue', len(overdue))
                    if overdue:
                        o=sorted(overdue, key=lambda r: -(now-int(r['next_sync_ts'])))[:5]
                        for r in o:
                            print('overdue_sample', r.get('base_label'), r.get('table_name'), 'overdue_sec', now-int(r['next_sync_ts']), 'last_sync_iso', r.get('last_sync_iso'))
                else:
                    print(str(data)[:500])
            except Exception:
                print(body[:500])
    except urllib.error.HTTPError as e:
        print('HTTP', url, e.code, e.read()[:200])
    except Exception as e:
        print('ERR', url, type(e).__name__, e)
