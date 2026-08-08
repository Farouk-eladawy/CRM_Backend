import json
echoes = []
with open('fb_webhook_debug.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        try:
            d = json.loads(line)
            for entry in d.get('entry', []):
                if 'messaging' in entry:
                    for msg in entry['messaging']:
                        if msg.get('message', {}).get('is_echo') or msg.get('sender', {}).get('id') == entry.get('id'):
                            echoes.append(msg)
                if 'changes' in entry:
                    for change in entry['changes']:
                        # maybe instagram or something?
                        pass
        except Exception as e:
            pass
print('Found', len(echoes), 'echoes')
if echoes: print(json.dumps(echoes[-1], indent=2, ensure_ascii=False))