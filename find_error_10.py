import sqlite3

def check_chat():
    db = sqlite3.connect('chat_history.db')
    c = db.cursor()
    
    print("--- Searching for error 10 at 2026-07-20 03:47 ---")
    # First, let's find the PSID and chat_id from agent_log.txt around 03:47
    import re
    psid = None
    try:
        with open('agent_log.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(reversed(lines)):
                if "Failed to send Facebook message" in line and "(#10)" in line and "03:47" in line:
                    actual_idx = len(lines) - 1 - i
                    # Look backwards to find the attempt
                    for j in range(actual_idx-1, max(-1, actual_idx-20), -1):
                        match = re.search(r'message to (\d+):', lines[j])
                        if match:
                            psid = match.group(1)
                            print(f"Found Attempt Log: {lines[j].strip()}")
                            break
                    break
    except FileNotFoundError:
        pass
        
    if not psid:
        print("Could not extract PSID from logs for this specific error.")
        return
        
    print(f"\nLooking up PSID {psid} in Database...")
    c.execute("SELECT chat_id, contact_name, last_message_time FROM conversations WHERE sender_identifier=?", (psid,))
    conv = c.fetchone()
    
    if conv:
        chat_id = conv[0]
        print(f"Customer Name: {conv[1]}")
        print(f"Last Customer Message Time: {conv[2]}")
        
        print("\nLast 5 messages sent by Customer:")
        c.execute("SELECT timestamp, text FROM messages WHERE chat_id=? AND sender_type='customer' ORDER BY timestamp DESC LIMIT 5", (chat_id,))
        for msg in c.fetchall():
            print(f"[{msg[0]}] {msg[1]}")
            
        print("\nLast 5 messages sent by Agent/System:")
        c.execute("SELECT timestamp, text FROM messages WHERE chat_id=? AND sender_type!='customer' ORDER BY timestamp DESC LIMIT 5", (chat_id,))
        for msg in c.fetchall():
            print(f"[{msg[0]}] {msg[1][:100]}...")
    else:
        print("Customer not found in DB.")

if __name__ == '__main__':
    check_chat()