import json
import sqlite3
import time
import os

target_id = "25879763984995048"
webhook_file = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\fb_webhook_debug.jsonl"
db_path = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\chat_history.db"

def get_latest_webhooks(num_lines=50):
    try:
        with open(webhook_file, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            return [json.loads(line) for line in lines[-num_lines:] if target_id in line or '"is_echo": true' in line]
    except Exception as e:
        print(f"Error reading webhook logs: {e}")
        return []

print(f"Waiting for new messages for ID: {target_id}...")
print("You can leave this running or just let the AI check the logs after the user says 'Done'.")
