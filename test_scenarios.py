import requests
import json
import time

BASE_URL = "http://localhost:5000"
CHAT_URL = f"{BASE_URL}/chat"

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_result(title, result, success=True):
    color = GREEN if success else RED
    print(f"\n{BLUE}=== {title} ==={RESET}")
    print(f"{color}{result}{RESET}")
    print("-" * 50)

def test_scenario(name, email, message, expected_keywords, context_desc):
    print(f"\nTesting Scenario: {YELLOW}{name}{RESET} ({context_desc})")
    payload = {
        "email": email,
        "message": message
    }
    
    try:
        start_time = time.time()
        response = requests.post(CHAT_URL, json=payload)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            reply = data.get("reply", "")
            booking_info = data.get("booking_info", {})
            
            # Check keywords
            found_all = True
            missing = []
            for kw in expected_keywords:
                if kw.lower() not in reply.lower():
                    found_all = False
                    missing.append(kw)
            
            status = "PASSED" if found_all else "FAILED"
            details = f"Reply:\n{reply}\n\nTime: {duration:.2f}s"
            
            if not found_all:
                details += f"\n\nMISSING KEYWORDS: {missing}"
            
            print_result(f"{name} [{status}]", details, success=found_all)
            return data
        else:
            print_result(f"{name} [ERROR]", f"Status Code: {response.status_code}\n{response.text}", success=False)
            return None
            
    except Exception as e:
        print_result(f"{name} [EXCEPTION]", str(e), success=False)
        return None

def run_tests():
    # 1. Existing Booking Test
    # Using a known booking ref from previous context: GYGWZBNABM2A
    # Assuming email 'ahmadyeladawy@gmail.com' is linked to it in Simulator logic
    test_scenario(
        "1. Booking Found",
        "ahmadyeladawy@gmail.com",
        "What time is my pickup?",
        ["pickup", "time"], # Expecting actual time or confirmation
        "Source: Official Booking Record"
    )

    # 2. New Trip Inquiry (Catalog Search)
    test_scenario(
        "2. New Trip Inquiry",
        "new_customer@example.com",
        "I want to book the Orange Bay trip. How much is it?",
        ["Orange Bay", "price", "include"],
        "Source: Internal Trips Catalog"
    )

    # 3. Complex/Policy Query (KB Search)
    test_scenario(
        "3. Policy Query",
        "new_customer@example.com", 
        "If I cancel my trip now, do I get a refund?",
        ["cancel", "24 hours", "refund"],
        "Source: Knowledge Base / Policy"
    )

    # 4. Complaint (Escalation Protocol)
    test_scenario(
        "4. Complaint Test",
        "ahmadyeladawy@gmail.com",
        "The driver was rude and asked for extra money!",
        ["apologize", "ticket", "investigation"],
        "Source: Complaint Protocol"
    )

    # 5. Web Search Fallback (External Info)
    # Asking something likely not in DB but findable on web
    test_scenario(
        "5. Web Search Test",
        "new_customer@example.com",
        "What is the weather usually like in Hurghada in January?",
        ["Hurghada", "weather", "degree", "wind"], 
        "Source: Web Search"
    )

if __name__ == "__main__":
    print(f"Starting System Tests on {BASE_URL}...")
    # Wait a bit to ensure server is ready if just restarted
    time.sleep(2) 
    run_tests()
