import logging
import sys
import os
import time
from datetime import datetime

# Setup logging to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Add parent directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_agent import AIAgent
from airtable_fields import FieldIds

def run_scenario():
    print("--- STARTING SCENARIO TEST ---")
    
    # 1. Initialize Agent
    try:
        agent = AIAgent()
        print("✔ Agent Initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Agent: {e}")
        return

    # User Details
    CUSTOMER_EMAIL = "Ahmadyeladawy@gmail.com"
    CUSTOMER_PHONE = "201010323484"
    
    # Scenario Steps
    conversation = [
        {
            "step": 1,
            "role": "user",
            "message": "Hello, what trips do you have available?",
            "expected_intent": "Inquiry"
        },
        {
            "step": 2,
            "role": "user",
            "message": "I want to book the Luxor trip for 2 adults on January 25th.",
            "expected_intent": "Booking"
        },
        {
            "step": 3,
            "role": "user",
            "message": "My hotel is Hilton Hurghada Plaza.",
            "expected_intent": "Update Info"
        },
        {
            "step": 4,
            "role": "user",
            "message": "Actually, I need to cancel this booking.",
            "expected_intent": "Cancellation"
        }
    ]

    # Session Context (Mocking what the API does)
    session_history = ""

    for turn in conversation:
        print(f"\n--- STEP {turn['step']}: User says '{turn['message']}' ---")
        
        try:
            # 1. Simulate Input Processing
            message = turn['message']
            
            # Find Booking (Simulate what the Chat Endpoint does)
            booking_record = agent.find_booking_strictly(
                message, 
                sender_email=CUSTOMER_EMAIL, 
                sender_phone=CUSTOMER_PHONE
            )
            
            if booking_record:
                print(f"   -> Found Booking ID: {booking_record['id']} (Table: {booking_record.get('table_name')})")
            else:
                print("   -> No existing booking found (New Lead?)")
                # Create Lead if not found (Logic from simulator_api.py)
                if turn['step'] == 1 or turn['step'] == 2:
                     if not booking_record:
                         print("   -> Creating Lead Record...")
                         booking_record = agent.create_lead_record(CUSTOMER_EMAIL, "Test User", message, phone=CUSTOMER_PHONE)
                         print(f"   -> Created Lead ID: {booking_record['id']}")

            # 2. Generate Reply
            # Mock History
            history_text = f"{session_history}\nUser: {message}"
            
            print("   -> Generating Smart Reply...")
            reply = agent.generate_smart_reply(
                history_text=history_text,
                kb_context=None, # Let it search internally if it wants
                latest_message_body=message,
                fallback_email=CUSTOMER_EMAIL,
                booking_record=booking_record
            )
            
            print(f"   -> AI Reply: {reply[:100]}...") # Print first 100 chars
            
            # Update Session
            session_history += f"\nUser: {message}\nAI: {reply}"

            # 3. Simulate Updates (The Critical Part where errors happen)
            if booking_record:
                print("   -> Attempting to Update Airtable Records...")
                
                # Chat Log Update
                agent.append_to_chat_log(
                    booking_record['id'], 
                    message, 
                    sender="User", 
                    source="Simulation", 
                    table_name=booking_record.get('table_name')
                )
                agent.append_to_chat_log(
                    booking_record['id'], 
                    reply, 
                    sender="AI", 
                    source="System", 
                    table_name=booking_record.get('table_name')
                )
                
                # Status Update (Mocking logic from simulator)
                updates = {}
                # Extract Intent (Mock extraction or use what generate_smart_reply might return if parsed)
                # For this test, we force the update to test the Field ID
                
                # Test Inquiry Type Update
                try:
                    print("   -> Updating Inquiry Type...")
                    agent.update_booking_record(
                        booking_record['id'], 
                        {FieldIds.INQUIRY_TYPE: "TEST_SCENARIO"}, 
                        table_name=booking_record.get('table_name')
                    )
                    print("   ✔ Inquiry Type Updated")
                except Exception as e:
                    print(f"   ❌ Failed to update Inquiry Type: {e}")

                # Test AI Chat Status
                try:
                    print("   -> Updating AI Chat Status...")
                    agent.update_booking_record(
                        booking_record['id'], 
                        {FieldIds.AI_CHAT_STATUS: "ACTIVE"}, 
                        table_name=booking_record.get('table_name')
                    )
                    print("   ✔ AI Chat Status Updated")
                except Exception as e:
                    print(f"   ❌ Failed to update AI Chat Status: {e}")
                    
        except Exception as e:
            print(f"❌ CRITICAL ERROR IN STEP {turn['step']}: {e}")
            import traceback
            traceback.print_exc()
            break # Stop on error to fix

    print("\n--- SCENARIO COMPLETE ---")

if __name__ == "__main__":
    run_scenario()
