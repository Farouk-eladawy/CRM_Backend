import json

with open('fb_webhook_debug.jsonl', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    print('Total lines:', len(lines))
    if lines:
        print('Last line:', lines[-1])

    # Let's count how many messaging events we have
    msg_count = 0
    for line in lines:
        try:
            d = json.loads(line)
            for entry in d.get('entry', []):
                for msg in entry.get('messaging', []):
                    msg_count += 1
        except Exception:
            pass
    print('Total messaging events:', msg_count)
