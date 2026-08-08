import json
import re
import sqlite3

def rigorous_log_check():
    print("--- STEP 1: EXTRACTING ALL 551 ERRORS FROM agent_log.txt ---")
    
    errors_found = []
    
    try:
        with open('agent_log.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            for i, line in enumerate(lines):
                if "Failed to send Facebook message" in line and "(#551)" in line:
                    error_time = line[:19]
                    
                    # Search backwards up to 30 lines to find the actual attempt
                    # It usually looks like "UI Agent sending Facebook message to [PSID]: [TEXT]"
                    # or it could be an automated message.
                    attempt_line = None
                    psid = None
                    
                    for j in range(i-1, max(-1, i-30), -1):
                        if "sending Facebook message to" in lines[j] or "Sending Facebook message to" in lines[j]:
                            attempt_line = lines[j].strip()
                            # Extract PSID
                            match = re.search(r'message to (\d+):', attempt_line)
                            if match:
                                psid = match.group(1)
                            break
                            
                    errors_found.append({
                        "error_time": error_time,
                        "raw_error": line.strip(),
                        "attempt_line": attempt_line,
                        "psid": psid
                    })
    except Exception as e:
        print(f"Error reading log: {e}")
        return

    for idx, e in enumerate(errors_found):
        print(f"\n[Error #{idx+1}] Time: {e['error_time']}")
        print(f"Attempt: {e['attempt_line']}")
        print(f"PSID extracted: {e['psid']}")

    print("\n--- STEP 2: LOOKING UP PSIDs IN DATABASE ---")
    db = sqlite3.connect('chat_history.db')
    c = db.cursor()
    
    unique_psids = set([e['psid'] for e in errors_found if e['psid']])
    
    for psid in unique_psids:
        print(f"\nInvestigating PSID: {psid}")
        c.execute("SELECT chat_id, contact_name, source, last_message_time FROM conversations WHERE sender_identifier=?", (psid,))
        conv = c.fetchone()
        if conv:
            chat_id = conv[0]
            print(f"  -> Chat ID: {chat_id}")
            print(f"  -> Contact Name: '{conv[1]}'")
            print(f"  -> Source: {conv[2]}")
            print(f"  -> Last Customer Message Time: {conv[3]}")
            
            print("  -> Last 3 Customer Messages:")
            c.execute("SELECT timestamp, text FROM messages WHERE chat_id=? AND sender_type='customer' ORDER BY timestamp DESC LIMIT 3", (chat_id,))
            for msg in c.fetchall():
                print(f"       [{msg[0]}] {msg[1]}")
                
            print("  -> Last 3 Agent/System Messages Sent:")
            c.execute("SELECT timestamp, sender_type, text FROM messages WHERE chat_id=? AND sender_type!='customer' ORDER BY timestamp DESC LIMIT 3", (chat_id,))
            for msg in c.fetchall():
                print(f"       [{msg[0]}] {msg[1]}: {msg[2][:100]}...")
        else:
            print("  -> NOT FOUND IN CONVERSATIONS TABLE.")

if __name__ == '__main__':
    rigorous_log_check()
