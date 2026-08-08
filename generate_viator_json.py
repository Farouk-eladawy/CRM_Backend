import json
import re

def generate_mock_data():
    input_file = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\Viator links.txt"
    output_file = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\Viator_data.json"
    
    tours = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for line in lines:
        if not line.strip(): continue
        
        # Split Title and URL (Assuming tab or space separated, but mostly just URL in some lines)
        # The file format seems to be: Title [tab] URL
        parts = line.strip().split('http')
        if len(parts) < 2: continue
        
        title_part = parts[0].strip()
        url = 'http' + parts[1].strip()
        
        # Extract Product Code (e.g., 14976P141)
        code_match = re.search(r'(\d+P\d+)', url)
        product_code = code_match.group(1) if code_match else "UNKNOWN"
        
        # If title is empty in the file, extract from URL slug
        if not title_part:
            # url like .../tours/Luxor/Private-Full-Day-Luxor-Tour.../d826...
            try:
                slug = url.split('/')[5] # approximation
                title_part = slug.replace('-', ' ')
            except:
                title_part = "Viator Tour"

        # Create Structured Data
        tour = {
            "tour_info": {
                "platform": "Viator",
                "url": url,
                "product_code": product_code,
                "title": title_part,
                "location": "Egypt",
                "category": "Tours",
                "breadcrumb": ["Home", "Egypt", "Tours"]
            },
            "pricing": {
                "price_from": 50.00, # Default mock price
                "currency": "USD",
                "price_unit": "per person",
                "discounted_rates_for_kids": True,
                "lowest_price_guarantee": True
            },
            "overview": {
                "description": f"Enjoy the {title_part}. This is a popular tour in Egypt provided by FTS Travels.",
                "duration": "Flexible",
                "start_time": "08:00 AM",
                "languages": ["English", "German", "Russian", "Italian"]
            },
            "features": {
                "pickup_offered": True,
                "mobile_ticket": True,
                "wheelchair_accessible": False,
                "private_tour": "Private" in title_part
            },
            "whats_included": [
                "Hotel pickup and drop-off",
                "Transport by air-conditioned vehicle",
                "Bottled water"
            ],
            "whats_not_included": [
                "Gratuities",
                "Personal expenses"
            ],
            "meeting_and_pickup": {
                "pickup_points": "Hotel Lobby",
                "pickup_details": "Please be ready at the lobby 15 minutes before departure.",
                "start_time": "08:00 AM"
            },
            "itinerary": [
                {
                    "stop": "Main Attraction",
                    "type": "Stop",
                    "description": "Visit the main highlights of the tour."
                }
            ],
            "supplier": {
                "name": "FTS Travels"
            },
            "cancellation_policy": {
                "description": "Free cancellation up to 24 hours before the experience starts.",
                "free_cancellation": "24 hours"
            },
             "booking_options": {
                "reserve_now_pay_later": True,
                "reserve_now_pay_later_description": "Secure your spot while staying flexible"
            }
        }
        tours.append(tour)
        
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(tours, f, indent=2, ensure_ascii=False)
        
    print(f"Generated {len(tours)} tours in {output_file}")

if __name__ == "__main__":
    generate_mock_data()
