import sys
import json
import logging
logging.basicConfig(level=logging.INFO)

import ai_agent

# Initialize the agent
agent = ai_agent.AIAgent()

# Fake a message
message_body = "Hello I want to ask about Umrah."
sender_phone = "+201012345678"
history_text = "User: Hello I want to ask about Umrah."
location = "Religious"

print("--- Testing process_unified_message ---")
result = agent.process_unified_message(
    sender_identifier=sender_phone,
    message_body=message_body,
    history_text=history_text,
    source="WhatsApp",
    subject=f"WhatsApp Message ({location})",
    location=location,
    receiving_phone_id="1129614400243143",
    skip_db_save=True
)

print("\n--- Result ---")
if result:
    print(json.dumps({k: v for k, v in result.items() if k != "booking_record"}, indent=2))
else:
    print("Result is None!")
