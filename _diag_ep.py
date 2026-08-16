import re, json
from pathlib import Path

# find force sync endpoints in code
files = ['ai_agent.py', 'airtable_mirror.py', 'automation_engine.py']
for fn in files:
    p = Path(fn)
    if not p.exists():
        continue
    lines = p.read_text(encoding='utf-8', errors='ignore').splitlines()
    for i,l in enumerate(lines,1):
        if re.search(r'force.?sync|mirror.*sync|/mirror|sync_mirror|airtable_mirror', l, re.I):
            if 'route' in l.lower() or '@app' in l or 'def ' in l or 'Blueprint' in l or '/api' in l or 'force' in l.lower():
                print(f'{fn}:{i}:{l[:200]}')

# broader grep for flask routes related to mirror
for p in Path('.').glob('*.py'):
    try:
        text = p.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        continue
    if 'mirror' not in text.lower():
        continue
    for i,l in enumerate(text.splitlines(),1):
        if ('@app.route' in l or '@bp.route' in l or 'add_url_rule' in l) and 'mirror' in l.lower():
            print('ROUTE', f'{p}:{i}:{l.strip()}')
        if re.search(r'force_?sync|sync_now|trigger.*sync', l, re.I):
            print('FORCE', f'{p}:{i}:{l.strip()[:220]}')
