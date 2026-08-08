import sqlite3
import requests
import urllib.parse

conn = sqlite3.connect('chat_history.db')
c = conn.cursor()
c.execute("SELECT chat_id, airtable_record_id, sender_identifier FROM conversations WHERE contact_name LIKE '%Andrew%'")
row = c.fetchone()
if row:
    chat_id, airtable_record_id, sender_identifier = row
    
    email = sender_identifier if '@' in sender_identifier else None
    if email and '<' in email and '>' in email:
        email = email.split('<')[1].split('>')[0].strip()
    
    main_conditions = []
    if airtable_record_id:
        main_conditions.append(f"RECORD_ID()='{airtable_record_id}'")
        
    if email:
        email_lower = email.lower().strip()
        main_conditions.append(f"LOWER({{Customer personal email}})='{email_lower}'")
        main_conditions.append(f"LOWER({{Customer Email}})='{email_lower}'")
        main_conditions.append(f"SEARCH('{email_lower}', LOWER({{Customer personal email}}))")
        main_conditions.append(f"SEARCH('{email_lower}', LOWER({{Customer Email}}))")

    formula = "OR(" + ",".join(main_conditions) + ")"
    print("Formula:", formula)
    
    # URL encode the formula
    url = "http://localhost:5001/api/customer_bookings/" + chat_id
    resp = requests.get(url)
    print("Response:", resp.json())
