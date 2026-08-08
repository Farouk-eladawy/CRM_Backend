import logging
from ai_agent import AIAgent

logging.basicConfig(level=logging.INFO)

def test_whatsapp_reply():
    print("--- Simulating WhatsApp Message from 201010323484 ---")
    agent = AIAgent()
    
    # 1. Simulate finding the booking (Strict Mode)
    # We want to ensure it finds the booking and generates a reply.
    phone = "201010323484"
    message = "Hello, please send me my tickets" # Testing the ticket logic as well
    
    print(f"\nIncoming Message: '{message}' from {phone}")
    
    # We call the main processing function
    # Note: process_unified_message requires history_text, but simulator_api calls it with history.
    # We will simulate calling find_booking_strictly first, as the API does.
    
    print("Step 1: Finding Booking...")
    rec = agent.find_booking_strictly(message, sender_phone=phone)
    
    if rec:
        print(f"Booking Found: {rec['id']}")
        # Now generate reply
        print("Step 2: Generating Reply...")
        # Since process_unified_message is complex and ties many things, 
        # let's call generate_smart_reply directly which is what process_unified_message calls eventually
        
        reply = agent.generate_smart_reply(
            rec=rec, 
            latest_message_body=message, 
            history_text="", # No history for test
            is_unverified_lead=False,
            kb_context="" # Add empty context
        )
        print(f"\n--- AI Response ---\n{reply}")
    else:
        print("Booking NOT found (Check if phone number is in Airtable).")

if __name__ == "__main__":
    test_whatsapp_reply()
