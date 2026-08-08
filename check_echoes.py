import json
echoes = 0
non_echoes = 0
total_events = 0
with open(r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\fb_webhook_debug.jsonl", 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get('object') == 'page':
                for entry in data.get('entry', []):
                    for event in entry.get('messaging', []):
                        total_events += 1
                        sender = event.get('sender', {}).get('id')
                        if str(sender) == '134596153060573':
                            msg = event.get('message', {})
                            if msg.get('is_echo'):
                                echoes += 1
                            else:
                                non_echoes += 1
        except Exception as e:
            pass
with open(r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\echoes_out.txt", "w") as f:
    f.write(f'Total Events: {total_events}, Echoes: {echoes}, Non-Echoes: {non_echoes}')