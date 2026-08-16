from pathlib import Path
import time

# focused log scan
paths = [
    Path('.dbg/teacher_service_restart.log'),
    Path('last_run_log.txt'),
    Path('religious_log.txt'),
    Path('looooooooooooog.txt'),
    Path('_thread_dump.txt'),
]
# also recent .log under .dbg and logs
for base in [Path('.dbg'), Path('logs'), Path('.')]:
    if not base.exists():
        continue
    for p in base.glob('*.log'):
        paths.append(p)
    for p in base.glob('*.out'):
        paths.append(p)

seen=set()
for p in paths:
    if not p.exists() or str(p) in seen:
        continue
    seen.add(str(p))
    try:
        text = p.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        print('readfail', p, e); continue
    lines = text.splitlines()
    interesting = []
    for i,l in enumerate(lines,1):
        low=l.lower()
        if any(x in low for x in ['mirror', 'airtable', 'sync failed', 'delta sync', 'traceback', 'error']):
            if 'mirror' in low or 'airtable' in low or 'delta sync' in low or 'full sync' in low:
                interesting.append((i,l[:260]))
    print('FILE', p, 'size', p.stat().st_size, 'mtime', time.ctime(p.stat().st_mtime), 'hits', len(interesting))
    for i,l in interesting[-30:]:
        print(f'  {i}:{l}')
