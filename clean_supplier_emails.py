import os
import json
from pyairtable import Api

def main():
    config_path = "config.json"
    if not os.path.exists(config_path):
        print("Config not found.")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    api = Api(config['airtable']['api_key'])
    base_id = config['airtable']['base_id']
    table_name = config['airtable']['tables']['main_list']
    table = api.table(base_id, table_name)

    # The field ID for Customer personal email
    EMAIL_FIELD_ID = "fldyn4LGMcYOPACtH"

    print("Fetching records...")
    records = table.all()
    
    domains_to_clean = ["pickalbatros.com", "getyourguide.com", "viator.com", "headout.com", "tripadvisor.com", "tiqets.com", "expedia.com", "booking.com"]
    
    updated_count = 0
    
    for rec in records:
        fields = rec.get("fields", {})
        email = fields.get(EMAIL_FIELD_ID, "")
        
        if email:
            email_lower = email.lower()
            if any(domain in email_lower for domain in domains_to_clean):
                print(f"Cleaning supplier email '{email}' from record {rec['id']} (Booking: {fields.get('fldZGLB1NXyaM530F', 'N/A')})")
                try:
                    # To clear the email, we set it to None or empty string
                    table.update(rec['id'], {EMAIL_FIELD_ID: ""})
                    updated_count += 1
                except Exception as e:
                    print(f"Failed to update {rec['id']}: {e}")

    print(f"Cleanup complete. Removed supplier emails from {updated_count} records.")

if __name__ == "__main__":
    main()
