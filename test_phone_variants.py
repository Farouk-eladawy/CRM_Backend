import logging
from ai_agent import AIAgent

logging.basicConfig(level=logging.INFO)

def test_robust_phone_lookup():
    print("\n--- Testing Robust Phone Lookup ---")
    agent = AIAgent()
    
    # Test Cases from User
    # Format: (Input Phone, Description)
    test_cases = [
        ("33651812108", "French Number (No +)"),
        ("+336 51812108", "French Number (With + and Space)"),
        ("(068) 359-8944", "US Format with parens"),
        ("+255 759 557 642", "Tanzania Format with spaces"),
        ("+49 15158754131", "German Format"),
        ("+1 (907) 440-1143", "US Format Complex"),
        ("07776747623", "UK Format")
    ]
    
    print("\n[Analysis] Generating Variants for Test Cases:")
    for phone, desc in test_cases:
        print(f"\nInput: {phone} ({desc})")
        variants = agent._generate_phone_variants(phone)
        print(f"Generated Variants: {variants}")
        
        # Simulate what query would look like
        print("Airtable Query Logic:")
        for p in variants:
            p_clean = p.replace('+', '').replace(' ', '')
            print(f"  - Exact Match: '{p}'")
            print(f"  - SEARCH Match: '{p_clean}'")
            if len(p_clean) >= 8:
                print(f"  - LAST-8 Match: '{p_clean[-8:]}'")

if __name__ == "__main__":
    test_robust_phone_lookup()
