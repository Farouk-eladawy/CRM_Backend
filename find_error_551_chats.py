import json
import sqlite3

def find_chats_for_error_551():
    print("Searching for error 551 in agent_log.txt to extract message contents...")
    
    # 1. Extract the text of the messages that failed from the log
    failed_texts = []
    try:
        with open('agent_log.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if "Failed to send Facebook message" in line and "(#551)" in line:
                    # Look slightly before the error to find the "UI Agent sending Facebook message to X: [TEXT]" log
                    start_idx = max(0, i - 15)
                    for j in range(i-1, start_idx, -1):
                        prev_line = lines[j]
                        if "UI Agent sending Facebook message to" in prev_line:
                            # Extract PSID and text
                            parts = prev_line.split("UI Agent sending Facebook message to")
                            if len(parts) > 1:
                                info = parts[1].strip()
                                psid_and_text = info.split(":", 1)
                                if len(psid_and_text) == 2:
                                    psid = psid_and_text[0].strip()
                                    text = psid_and_text[1].strip()
                                    failed_texts.append({"psid": psid, "text": text, "log_time": line[:19]})
                                break
    except FileNotFoundError:
        print("agent_log.txt not found.")
        return

    if not failed_texts:
        print("Could not find the original message texts in the log.")
        return

    # 2. Look up these PSIDs in the database to get Customer Names
    print(f"Found {len(failed_texts)} failed attempts. Looking up customer details...\n")
    
    db = sqlite3.connect('chat_history.db')
    c = db.cursor()
    
    for item in failed_texts:
        psid = item['psid']
        c.execute("SELECT chat_id, contact_name, last_message_time FROM conversations WHERE sender_identifier=?", (psid,))
        row = c.fetchone()
        
        print("-" * 50)
        print(f"⏰ توقيت الخطأ: {item['log_time']}")
        if row:
            print(f"👤 اسم العميل (Contact Name): {row[1]}")
            print(f"🆔 معرف العميل (PSID): {psid}")
            print(f"🕒 آخر رسالة من العميل: {row[2]}")
            print(f"💬 النص الذي حاول الموظف إرساله:\n{item['text'][:150]}...")
        else:
            print(f"🆔 معرف العميل (PSID): {psid} (لم يتم العثور على اسم في قاعدة البيانات)")
            print(f"💬 النص الذي حاول الموظف إرساله:\n{item['text'][:150]}...")

if __name__ == '__main__':
    find_chats_for_error_551()
