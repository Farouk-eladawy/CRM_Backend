import logging
import sys
import os
from ai_agent import AIAgent, FieldIds

# Setup logging
logging.basicConfig(level=logging.INFO)

# Initialize Agent
agent = AIAgent()

# Booking Reference from User Report
BOOKING_REF = "BR-45454845"

print(f"--- Checking Booking {BOOKING_REF} ---")

# 1. Find Booking
record = agent.find_booking_by_number(BOOKING_REF)

if record:
    print(f"✔ Booking Found: {record['id']}")
    fields = record['fields']
    
    # 2. Check Attachments
    attachments = fields.get(FieldIds.ATTACHMENTS)
    if attachments:
        print(f"✔ Attachments Found: {len(attachments)}")
        for i, att in enumerate(attachments):
            print(f"   [{i+1}] {att.get('filename')} - {att.get('url')}")
            
        # 3. Test Ticket Processing (Cloudinary Upload)
        print("\n--- Testing Ticket Processing Logic ---")
        reply, success = agent.process_ticket_request(record)
        print(f"Result Success: {success}")
        print(f"Reply Generated:\n{reply}")
        
    else:
        print("❌ No Attachments Found in Airtable Record.")
else:
    print("❌ Booking Record Not Found.")
