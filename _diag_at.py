import json, os, urllib.parse, urllib.request
from pathlib import Path

api_key = base_id = None
src = None
root = Path('.')
# config.json
if Path('config.json').exists():
    c = json.loads(Path('config.json').read_text(encoding='utf-8'))
    air = c.get('airtable') if isinstance(c.get('airtable'), dict) else {}
    if air:
        api_key = air.get('api_key') or air.get('token') or air.get('pat')
        base_id = air.get('base_id') or air.get('baseId') or (air.get('bases') or {}).get('main')
        src = 'config.json:airtable'
        if isinstance(air.get('bases'), dict) and not base_id:
            # common shape
            for k,v in air['bases'].items():
                if k == 'main' and isinstance(v, str):
                    base_id = v
                elif isinstance(v, dict) and v.get('base_id'):
                    if k == 'main':
                        base_id = v.get('base_id')
    # flat keys
    for k,v in c.items():
        kl = str(k).lower()
        if api_key is None and 'airtable' in kl and any(x in kl for x in ('key','token','pat','api')):
            api_key = str(v); src = f'config.json:{k}'
        if base_id is None and 'airtable' in kl and 'base' in kl and isinstance(v, str):
            base_id = v
    if isinstance(c.get('bases'), dict) and not base_id:
        base_id = c['bases'].get('main')

if Path('.env').exists():
    for line in Path('.env').read_text(encoding='utf-8', errors='ignore').splitlines():
        if '=' not in line or line.strip().startswith('#'):
            continue
        k,v = line.split('=',1)
        k=k.strip(); v=v.strip().strip('"').strip("'")
        kl=k.lower()
        if api_key is None and 'airtable' in kl and any(x in kl for x in ('key','token','pat','api')):
            api_key = v; src = f'.env:{k}'
        if base_id is None and 'airtable' in kl and 'base' in kl:
            base_id = v

# from mirror table_key we already know base appTp5YgSp9DV2HYc
if not base_id:
    base_id = 'appTp5YgSp9DV2HYc'
    print('base_id_fallback_from_mirror', base_id)

print('api_key_source', src)
print('api_key_last4', api_key[-4:] if api_key else None)
print('base_id', base_id)

if not api_key:
    # try ai_agent style env names inside config nested
    print('MISSING_API_KEY')
else:
    formula = "{Booking Nr.}='33416130'"
    params = urllib.parse.urlencode({'filterByFormula': formula, 'maxRecords': 5})
    url = f'https://api.airtable.com/v0/{base_id}/List?{params}'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {api_key}'})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        recs = data.get('records') or []
        print('found_count', len(recs))
        for r in recs:
            f = r.get('fields') or {}
            # find create date key with trailing spaces
            create_keys = [k for k in f if 'create' in k.lower() and 'date' in k.lower()]
            mod_keys = [k for k in f if 'modif' in k.lower()]
            print('record_id', r.get('id'))
            print('createdTime', r.get('createdTime'))
            for ck in create_keys:
                print('FIELD', repr(ck), f.get(ck))
            for mk in mod_keys:
                print('FIELD', repr(mk), f.get(mk))
            for name in ('Booking Status','Agency','Date Trip','Booking Nr.'):
                print(name, f.get(name))
    except Exception as e:
        print('AIRTABLE_ERROR', type(e).__name__, e)
        if hasattr(e, 'read'):
            try:
                print('body', e.read().decode('utf-8', errors='replace')[:1000])
            except Exception:
                pass
