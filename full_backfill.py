import sqlite3
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import chat_db
from ai_agent import AIAgent
from airtable_fields import FieldIds

def full_backfill_and_repair():
    print("Starting full DB backfill and repair...")
    agent = AIAgent()
    
    with sqlite3.connect(chat_db.DB_FILE, timeout=15.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Select all conversations that have an airtable_record_id
        c.execute("SELECT * FROM conversations WHERE airtable_record_id IS NOT NULL AND airtable_record_id != ''")
        rows = c.fetchall()
        
        print(f"Found {len(rows)} linked conversations to check.")
        
        updated = 0
        for row in rows:
            chat_id = row['chat_id']
            record_id = row['airtable_record_id']
            current_name = row['contact_name']
            current_booking = row['booking_number']
            receiving_phone_id = row['receiving_phone_id']
            
            try:
                record = agent._get_record_from_any_table(record_id)
                if not record:
                    continue
                
                fields = record.get('fields', {})
                
                # Extract correct name
                real_name = agent.get_field_value(fields, FieldIds.CUSTOMER_NAME)
                # If not found, try Arabic field 'الاسم' for religious table
                if not real_name:
                    real_name = fields.get('الاسم')
                
                # Extract correct booking number
                real_booking = agent.get_field_value(fields, FieldIds.BOOKING_NR)
                if not real_booking:
                    real_booking = fields.get('رقم الجواز')
                
                # Extract correct location
                db_location = agent._derive_chat_location_from_fields(
                    fields,
                    fallback_location=row['location'],
                    receiving_phone_id=receiving_phone_id
                )
                
                needs_update = False
                update_kwargs = {}
                
                if real_name and (current_name == "Guest" or not current_name or "Guest" in current_name):
                    update_kwargs['contact_name'] = real_name
                    needs_update = True
                    
                if real_booking and (current_booking is None or current_booking == ""):
                    update_kwargs['booking_number'] = real_booking
                    needs_update = True
                    
                if db_location and db_location != row['location']:
                    update_kwargs['location'] = db_location
                    needs_update = True
                    
                if needs_update:
                    chat_db.update_conversation_info(chat_id, **update_kwargs)
                    updated += 1
                    print(f"Updated chat {chat_id}: {update_kwargs}")
                    
            except Exception as e:
                print(f"Error repairing chat {chat_id} (Record: {record_id}): {e}")
                
        print(f"Finished full backfill. Updated {updated} conversations.")

if __name__ == '__main__':
    full_backfill_and_repair()
