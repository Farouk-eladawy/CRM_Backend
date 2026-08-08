import json

keys = set()
with open(r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\fb_webhook_debug.jsonl", 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        try:
            data = json.loads(line)
            for entry in data.get('entry', []):
                keys.update(entry.keys())
        except:
            pass
print(keys)