import json

echo_examples = []
with open(r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\fb_webhook_debug.jsonl", 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get('object') == 'page':
                for entry in data.get('entry', []):
                    entry_page_id = str(entry.get('id', ''))
                    for event in entry.get('messaging', []):
                        message = event.get('message', {})
                        raw_sender = str(event.get('sender', {}).get('id', ''))
                        is_echo = message.get('is_echo', False)
                        if not is_echo and raw_sender == entry_page_id:
                            is_echo = True
                            
                        if is_echo:
                            echo_examples.append(event)
                            if len(echo_examples) >= 3:
                                break
                    if len(echo_examples) >= 3:
                        break
            if len(echo_examples) >= 3:
                break
        except Exception:
            pass

with open(r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\echo_samples.txt", 'w', encoding='utf-8') as out:
    for ex in echo_examples:
        out.write(json.dumps(ex, ensure_ascii=False, indent=2) + "\n")
