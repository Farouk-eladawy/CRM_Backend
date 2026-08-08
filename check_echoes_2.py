import json
found = False
with open(r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\fb_webhook_debug.jsonl", 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        if '"is_echo": true' in line and '"app_id": 263902037430900' not in line:
            found = True
            break
with open("result.txt", "w") as f:
    f.write(str(found))