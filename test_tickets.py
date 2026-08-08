import logging
from ai_agent import AIAgent

logging.basicConfig(level=logging.INFO)

def test_ticket_request():
    print("\n--- Testing Ticket Request Flow ---")
    agent = AIAgent()
    
    # 1. Simulate a request with NO attachments (Should Escalate)
    # We use a known booking or simulate one
    print("\n[Test 1] Testing with booking that has NO attachments...")
    # I'll create a fake record dict to avoid hitting Airtable API limit/dependency for this unit test
    fake_record_no_att = {
        'id': 'recTEST_NO_ATT',
        'fields': {
            'Booking Nr.': 'TEST-123',
            'Customer Name': 'Test User'
            # No 'Attachments'
        }
    }
    
    reply, success = agent.process_ticket_request(fake_record_no_att)
    print(f"Result (Should be False): {success}")
    print(f"Reply: {reply}")
    
    # 2. Simulate a request WITH attachments (Should Upload)
    print("\n[Test 2] Testing with booking that HAS attachments...")
    # NOTE: To really test this, we need a valid URL. 
    # I will use a dummy image URL that is publicly accessible.
    fake_record_att = {
        'id': 'recTEST_WITH_ATT',
        'fields': {
            'Booking Nr.': 'TEST-456',
            'Customer Name': 'Test User',
            'fldlnGdLQW6lgZdhP': [ # Using the actual Field ID for Attachments from airtable_fields.py
                {
                    'url': 'https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg',
                    'filename': 'sample_ticket.jpg'
                }
            ]
        }
    }
    
    reply_att, success_att = agent.process_ticket_request(fake_record_att)
    print(f"Result (Should be True): {success_att}")
    print(f"Reply: {reply_att}")

if __name__ == "__main__":
    test_ticket_request()
