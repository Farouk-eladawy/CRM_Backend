import json
import sqlite3
import os

target_id = "25879763984995048"
webhook_file = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\fb_webhook_debug.jsonl"
db_path = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\chat_history.db"

print(f"--- Checking Webhook Logs for ID: {target_id} ---")
try:
    with open(webhook_file, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
        
    found_webhooks = []
    for line in lines[-1000:]:  # Check the last 1000 lines
        if target_id in line:
            found_webhooks.append(json.loads(line))
            
    if not found_webhooks:
        print("No webhook events found for this ID in the recent logs.")
    else:
        for wh in found_webhooks:
            print(json.dumps(wh, ensure_ascii=False))
except Exception as e:
    print(f"Error reading webhook logs: {e}")

print(f"\n--- Checking Database for ID: {target_id} ---")
try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get chat_id
    c.execute("SELECT chat_id FROM conversations WHERE sender_identifier = ?", (target_id,))
    chat_row = c.fetchone()
    
    if not chat_row:
        print("No conversation found in the database for this ID.")
    else:
        chat_id = chat_row['chat_id']
        print(f"Found conversation: {chat_id}")
        
        c.execute("SELECT sender_type, text, timestamp, source FROM messages WHERE chat_id = ? ORDER BY timestamp DESC LIMIT 10", (chat_id,))
        messages = c.fetchall()
        
        if not messages:
            print("No messages found for this conversation.")
        else:
            for msg in messages:
                print(f"[{msg['timestamp']}] {msg['sender_type']} ({msg['source']}): {msg['text']}")
                
except Exception as e:
    print(f"Error reading database: {e}")
finally:
    if 'conn' in locals():
        conn.close()
