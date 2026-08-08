import os
with open("fb_webhook_debug.jsonl", "r", encoding="utf-8") as f:
    lines = f.readlines()
    print("Total lines:", len(lines))
    for line in lines[-5:]:
        print(line.strip())
