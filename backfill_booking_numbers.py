import sqlite3
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import chat_db
from ai_agent import AIAgent
from airtable_fields import FieldIds

def backfill_booking_numbers():
    print("Starting booking_number backfill...")
    agent = AIAgent()
    
    with sqlite3.connect(chat_db.DB_FILE, timeout=15.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute("SELECT chat_id, airtable_record_id FROM conversations WHERE airtable_record_id IS NOT NULL AND airtable_record_id != '' AND (booking_number IS NULL OR booking_number = '')")
        rows = c.fetchall()
        
        print(f"Found {len(rows)} conversations to check.")
        
        updated = 0
        for row in rows:
            chat_id = row['chat_id']
            record_id = row['airtable_record_id']
            
            try:
                # Get from Airtable
                record = agent.table.get(record_id)
                booking_nr = record['fields'].get(FieldIds.BOOKING_NR)
                
                if not booking_nr:
                    # fallback to leads
                    fallback_table = agent.airtable_api.table(agent.config.get('airtable', {}).get('base_id'), "Leads")
                    try:
                        record = fallback_table.get(record_id)
                        booking_nr = record['fields'].get(FieldIds.BOOKING_NR)
                    except Exception as fallback_e:
                        pass
                        # print(f"Fallback error for {record_id}: {fallback_e}")
                
                if booking_nr:
                    c.execute("UPDATE conversations SET booking_number = ? WHERE chat_id = ?", (booking_nr, chat_id))
                    conn.commit()
                    updated += 1
                    print(f"Updated chat {chat_id} with booking number {booking_nr}")
                else:
                    # print(f"No booking_nr found for {record_id}")
                    pass
            except Exception as e:
                pass
                # print(f"Error fetching record {record_id}: {e}")
                
        print(f"Finished backfill. Updated {updated} conversations.")

if __name__ == '__main__':
    backfill_booking_numbers()
