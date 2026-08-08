import sqlite3
import os
import sys
import json

def sync_locations():
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from pyairtable import Api
    from airtable_fields import FieldIds
    
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    api = Api(config['airtable']['api_key'])
    table = api.table(config['airtable']['base_id'], config['airtable']['tables']['main_list'])
    
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    
    c.execute("SELECT chat_id, airtable_record_id, location FROM conversations WHERE airtable_record_id IS NOT NULL AND airtable_record_id != ''")
    conversations = c.fetchall()
    
    updated_count = 0
    for chat_id, record_id, current_loc in conversations:
        try:
            record = table.get(record_id)
            des = record.get('fields', {}).get('des', '')
            
            new_loc = "Hurghada/Cairo"
            if des and "sharm" in str(des).lower():
                new_loc = "Sharm"
                
            if new_loc != current_loc:
                c.execute("UPDATE conversations SET location = ? WHERE chat_id = ?", (new_loc, chat_id))
                updated_count += 1
                print(f"Updated chat {chat_id} (Record {record_id}) from {current_loc} to {new_loc} based on DES='{des}'")
        except Exception as e:
            pass
            # print(f"Error fetching record {record_id}: {e}")
            
    conn.commit()
    print(f"Sync complete. Updated {updated_count} conversations based on Airtable Destination field.")

if __name__ == "__main__":
    sync_locations()
