import json
import time
from datetime import datetime

# Read the last 500 lines of fb_webhook_debug.jsonl to verify
lines = []
with open(r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\fb_webhook_debug.jsonl", "r", encoding="utf-8", errors="replace") as f:
    # Read the whole file and get the last 500 lines
    all_lines = f.readlines()
    lines = all_lines[-500:]

echo_count = 0
for line in lines:
    if "is_echo" in line:
        echo_count += 1
        data = json.loads(line)
        timestamp = data['entry'][0]['time']
        print(f"Found echo at timestamp: {timestamp} -> {datetime.fromtimestamp(timestamp/1000).strftime('%Y-%m-%d %H:%M:%S')}")

if echo_count == 0:
    print("No echoes found in the last 500 webhook events.")
