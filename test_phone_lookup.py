import logging
from ai_agent import AIAgent

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_phone_lookup():
    print("Initializing AI Agent...")
    try:
        agent = AIAgent()
        
        phone_to_test = "201010323484"
        print(f"\n--- Testing Lookup for Phone: {phone_to_test} ---")
        
        # Test 1: Direct Contact Lookup
        print("\n[Test 1] calling find_booking_by_contact directly...")
        rec = agent.find_booking_by_contact(phone=phone_to_test)
        
        if rec:
            print(f"✅ SUCCESS: Found Booking via find_booking_by_contact!")
            print(f"   ID: {rec.get('id')}")
            fields = rec.get('fields', {})
            print(f"   Customer Name: {fields.get('Customer Name')}")
            print(f"   Customer Phone: {fields.get('Customer Phone')}")
            print(f"   Booking Nr: {fields.get('Booking Nr.')}")
        else:
            print(f"❌ FAILED: find_booking_by_contact returned None.")

        # Test 2: Unified Strict Lookup (simulating WhatsApp flow)
        print(f"\n[Test 2] calling find_booking_strictly (Simulating WhatsApp)...")
        # Passing it as sender_phone is key here
        rec_strict = agent.find_booking_strictly(
            message_text="Hello check my booking", 
            sender_phone=phone_to_test
        )
        
        if rec_strict:
            print(f"✅ SUCCESS: Found Booking via find_booking_strictly!")
            print(f"   ID: {rec_strict.get('id')}")
        else:
            print(f"❌ FAILED: find_booking_strictly returned None.")

    except Exception as e:
        print(f"An error occurred during testing: {e}")

if __name__ == "__main__":
    test_phone_lookup()
