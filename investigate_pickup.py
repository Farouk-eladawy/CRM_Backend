import os
import json
import sqlite3
from pyairtable import Api

def main():
    try:
        # Load config
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        
        api = Api(cfg["airtable"]["api_key"])
        base_id = cfg["airtable"]["base_id"]
        table_name = cfg["airtable"]["tables"]["main_list"]
        table = api.table(base_id, table_name)
        
        # 1. Fetch from Airtable
        booking_nr = 'GYGG45RBHQ46'
        print(f"--- Searching Airtable for Booking: {booking_nr} ---")
        records = table.all(formula=f"{{Booking Nr.}}='{booking_nr}'")
        if not records:
            print("No records found in Airtable.")
            return
            
        rec = records[0]
        rid = rec['id']
        fields = rec['fields']
        print(f"Found Record ID: {rid}")
        print("Relevant Fields:")
        for k in ["Customer Name", "trip Name", "Send Sharm Pickup", "Pickup Scheduled", "Send HC Pickup", "Status Photographer WhatsApp", "Booking Pickup HC", "Booking Pickup Sharm"]:
            if k in fields:
                print(f"  {k}: {fields[k]}")
                
        # 2. Check chat database
        db_path = os.path.join(os.path.dirname(__file__), 'chat_history.db')
        if os.path.exists(db_path):
            print(f"\n--- Checking chat_history.db for record {rid} ---")
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT chat_id FROM conversations WHERE airtable_record_id=?", (rid,))
            chat_rows = c.fetchall()
            for chat in chat_rows:
                chat_id = chat['chat_id']
                print(f"Chat ID: {chat_id}")
                c.execute("SELECT timestamp, sender_type, text, source FROM messages WHERE chat_id=? ORDER BY timestamp ASC", (chat_id,))
                msgs = c.fetchall()
                for m in msgs:
                    if 'Pickup' in m['text'] or 'بيك اب' in m['text'] or m['sender_type'] == 'agent':
                        snippet = m['text'].replace('\n', ' ')[:80]
                        print(f"  [{m['timestamp']}] {m['sender_type']} ({m['source']}): {snippet}...")
                        
            conn.close()
        else:
            print("chat_history.db not found.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
