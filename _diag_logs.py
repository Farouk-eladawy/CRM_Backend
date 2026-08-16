import os, re
from pathlib import Path
from datetime import datetime

root = Path('.')
patterns = ['Mirror delta sync failed', 'Mirror full sync failed', 'Mirror List ID reconcile failed', 'delta sync', 'airtable_mirror', 'sync failed']
# collect candidate log files
cands = []
for p in root.rglob('*'):
    if not p.is_file():
        continue
    name = p.name.lower()
    if p.suffix.lower() in ('.log', '.txt', '.out') or 'log' in name or 'railway' in name:
        try:
            st = p.stat()
        except Exception:
            continue
        # recently modified today-ish or size reasonable
        if st.st_size > 50_000_000:
            continue
        cands.append((st.st_mtime, st.st_size, p))

cands.sort(reverse=True)
print('CANDIDATE_LOGS', len(cands))
for mtime, size, p in cands[:40]:
    print(time_ctime := __import__('time').ctime(mtime), size, p)

hits = []
for mtime, size, p in cands[:60]:
    try:
        text = p.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        continue
    for i, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        if any(pat.lower() in low for pat in patterns):
            hits.append((mtime, str(p), i, line[:300]))

print('HIT_COUNT', len(hits))
# prefer today Aug 13
for mtime, path, i, line in sorted(hits, key=lambda x: -x[0])[:40]:
    print(__import__('time').ctime(mtime), f'{path}:{i}', line)
