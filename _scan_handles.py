import psutil
print("=== ALL processes with chat_history.db or airtable_mirror.db open ===")
for p in psutil.process_iter(['pid','name','cmdline']):
    try:
        files = [f.path for f in p.open_files()]
    except Exception:
        continue
    hits = [f for f in files if 'chat_history.db' in f or 'airtable_mirror.db' in f]
    if hits:
        cmd = ' '.join(p.info['cmdline'] or [])[:90]
        short = [h.split('\\')[-1] for h in hits]
        print(p.info['pid'], '|', p.info['name'], '|', cmd, '|', short)
