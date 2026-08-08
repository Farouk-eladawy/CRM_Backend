import sys
import traceback
import sqlite3
import os
import json

log_file = r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\bulletproof_log.txt"

try:
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("Starting script...\n")
        db_path = r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\chat_history.db"
        if not os.path.exists(db_path):
            f.write(f"DB NOT FOUND at {db_path}\n")
        else:
            f.write("DB found, connecting...\n")
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            f.write("=== RECENT FACEBOOK AGENT MESSAGES ===\n")
            c.execute("SELECT id, chat_id, text, timestamp FROM messages WHERE source='Facebook' AND sender_type='agent' ORDER BY timestamp DESC LIMIT 10")
            for row in c.fetchall():
                f.write(str(row) + "\n")

            f.write("=== RECENT FACEBOOK CUSTOMER MESSAGES ===\n")
            c.execute("SELECT id, chat_id, text, timestamp FROM messages WHERE source='Facebook' AND sender_type='customer' ORDER BY timestamp DESC LIMIT 5")
            for row in c.fetchall():
                f.write(str(row) + "\n")
                
            conn.close()
            f.write("DB queries completed successfully.\n")

        # Also get echo examples from fb_webhook_debug.jsonl
        f.write("\n=== FB WEBHOOK ECHO EXAMPLES ===\n")
        echo_examples = []
        with open(r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\fb_webhook_debug.jsonl", 'r', encoding='utf-8', errors='ignore') as logf:
            for line in logf:
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
                except Exception as e:
                    pass

        for ex in echo_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
            
        f.write("Finished.\n")

except Exception as e:
    with open(log_file, "a", encoding="utf-8") as f:
        f.write("EXCEPTION OCCURRED:\n")
        f.write(traceback.format_exc() + "\n")
