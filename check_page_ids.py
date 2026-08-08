import json
page_ids = set()
with open(r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\fb_webhook_debug.jsonl", 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get('object') == 'page':
                for entry in data.get('entry', []):
                    page_ids.add(entry.get('id'))
        except:
            pass
with open("page_ids_out.txt", "w") as f:
    f.write(str(page_ids))