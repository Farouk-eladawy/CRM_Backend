import json
import os

FILE_PATH = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\Viator_data.json"

# البيانات الجديدة التي زودتني بها
NEW_DATA_MAP = {
    "14976P141": {
        "tour_info": {
            "platform": "Viator",
            "url": "https://www.viator.com/tours/Luxor/Private-Full-Day-Luxor-Tour-Customize-Your-Adventure/d826-14976P141",
            "product_code": "14976P141",
            "title": "Private Luxor Day Tour W/Horse Carriage Ride & Flexible Itinerary",
            "location": "Luxor, Egypt",
            "category": "Full-day Tours",
            "breadcrumb": ["Home", "Things to do in Egypt", "Things to do in Luxor", "Luxor Tours", "Full-day Tours"]
        },
        "pricing": {
            "price_from": 30.00,
            "currency": "USD",
            "price_unit": "per person",
            "discounted_rates_for_kids": True,
            "lowest_price_guarantee": True
        },
        "overview": {
            "description": "Experience a fully customizable private Luxor tour with a horse-drawn carriage ride, private vehicle, flexible itinerary, and expert local guidance.",
            "duration": "8 hours (approx.)",
            "start_time": "8:00 am",
            "languages": ["English", "German", "Russian", "Italian"]
        },
        "features": {
            "pickup_offered": True,
            "mobile_ticket": True,
            "wheelchair_accessible": False,
            "private_tour": True,
            "group_discounts": True,
            "free_cancellation": True
        },
        "whats_included": [
            "Private air-conditioned vehicle for the entire day",
            "Hotel pickup and drop-off anywhere in Luxor",
            "Professional driver with local knowledge",
            "Bottled water during the tour",
            "Flexible itinerary tailored to your preferences",
            "Optional private guide (available upon request)",
            "All local taxes and service fees",
            "Traditional horse-drawn carriage ride (Calèche) around Luxor"
        ],
        "whats_not_included": [
            "Entrance fees to all temples, tombs, and museums (paid at each site)",
            "Lunch or any meals during the tour",
            "Gratuities",
            "Personal expenses",
            "Optional activities"
        ],
        "meeting_and_pickup": {
            "pickup_points": "Select a pickup point",
            "pickup_details": "Hotel pickup is included from any accommodation in Luxor. Your driver will meet you at your hotel lobby at the agreed time. Please provide your hotel name, room number, and preferred pickup time when booking.",
            "start_time": "8:00 am"
        },
        "itinerary": [
            {
                "stop": "Valley of the Kings",
                "type": "Pass By",
                "description": "Explore the tombs of ancient pharaohs, including Tutankhamun's tomb (entrance fee not included). Admire intricate hieroglyphs and burial chambers."
            },
            {
                "stop": "Temple of Hatshepsut at Deir el Bahari",
                "type": "Pass By",
                "description": "Visit the mortuary temple of Egypt's famous female pharaoh. See the unique colonnaded terraces and statues."
            },
            {
                "stop": "Colossi of Memnon",
                "type": "Pass By",
                "description": "Stop for photos at the two giant statues of Pharaoh Amenhotep III. Iconic landmark at the entrance to the Theban Necropolis."
            },
            {
                "stop": "Temple of Karnak",
                "type": "Pass By",
                "description": "Walk through the largest temple complex in Egypt. See the Hypostyle Hall, Obelisks, and sacred lake."
            }
        ],
        "additional_info": [
            "Confirmation will be received at time of booking",
            "Not wheelchair accessible",
            "Infants must sit on laps",
            "Not recommended for pregnant travelers",
            "Not recommended for travelers with back problems",
            "No heart problems or other serious medical conditions",
            "Most travelers can participate",
            "This is a private tour/activity. Only your group will participate"
        ],
        "supplier": {
            "name": "FTS Travels"
        },
        "cancellation_policy": {
            "description": "You can cancel up to 24 hours in advance of the experience for a full refund.",
            "free_cancellation": "up to 24 hours before the experience starts (local time)"
        },
        "booking_options": {
            "reserve_now_pay_later": True,
            "reserve_now_pay_later_description": "Secure your spot while staying flexible"
        }
    },
    "14976P140": {
        "tour_info": {
            "platform": "Viator",
            "url": "https://www.viator.com/tours/Marsa-Alam/Cairo-Day-Tour-by-Plane-from-Marsa-Alam/d25556-14976P140",
            "product_code": "14976P140",
            "title": "Cairo Day Tour by Plane from Marsa Alam",
            "location": "Marsa Alam, Egypt",
            "category": "Overnight Tours",
            "breadcrumb": ["Home", "Things to do in Egypt", "Things to do in Red Sea", "Things to do in Marsa Alam", "Marsa Alam Tours", "Overnight Tours"]
        },
        "pricing": {
            "price_from": 260.00,
            "currency": "USD",
            "price_unit": "per person",
            "discounted_rates_for_kids": True,
            "lowest_price_guarantee": True
        },
        "overview": {
            "description": "Explore the wonders of Cairo on this full-day tour from Marsa Alam by plane. Visit the iconic Pyramids of Giza and the Sphinx, then immerse yourself in ancient history at the Egyptian Museum. Enjoy guided sightseeing with a traditional lunch included, ensuring a comprehensive experience of Cairo's highlights. Small group sizes make for a personalized adventure, perfect for travelers looking to maximize their day in this historic city.",
            "duration": "1 day (approx.)",
            "start_time": "3:00 am",
            "languages": ["English", "and 5 more"]
        },
        "features": {
            "pickup_offered": True,
            "mobile_ticket": True,
            "wheelchair_accessible": False,
            "private_tour": False,
            "group_discounts": True,
            "free_cancellation": True
        },
        "whats_included": [
            "Hotel pickup and drop-off in Marsa Alam",
            "Round-trip domestic flights (Hurghada ↔ Cairo)",
            "All transfers in air-conditioned vehicles",
            "Professional Egyptologist tour guide",
            "Entrance fees to Egyptian Museum",
            "Traditional lunch at local restaurant",
            "All taxes and service charges",
            "Bottled water during the tour",
            "Airport assistance"
        ],
        "whats_not_included": [
            "Entrance fees to Giza Pyramids",
            "Optional activities",
            "Drinks during lunch",
            "Personal expenses",
            "Gratuities"
        ],
        "meeting_and_pickup": {
            "pickup_points": "Marsa Alam, Red Sea Governorate, Egypt",
            "pickup_details": "Guests will be picked up early in the morning from their hotel in Marsa Alam. Pickup times will be confirmed the day before the tour. Our driver will assist you reach the airport comfortably.",
            "start_time": "3:00 am"
        },
        "itinerary": [
            {
                "stop": "Marsa Alam",
                "type": "Stop",
                "description": "You will be picked up from your hotel in Marsa Alam in the early morning and transferred by air-conditioned vehicle to Hurghada Airport."
            },
            {
                "stop": "Hurghada",
                "type": "Stop",
                "description": "Flight from Hurghada to Cairo"
            },
            {
                "stop": "Cairo Airport",
                "type": "Pass By",
                "description": "Upon arrival at Cairo Airport, you will meet your professional Egyptologist tour guide, who will accompany you throughout the day."
            },
            {
                "stop": "The Egyptian Museum in Cairo",
                "type": "Stop",
                "description": "Visit the Egyptian Museum, which houses an extensive collection of ancient Egyptian artifacts, including treasures from the tomb of King Tutankhamun."
            },
            {
                "stop": "Giza Pyramids & Sphinx",
                "type": "Stop",
                "description": "Visit the iconic Giza Plateau, home to the Great Pyramid of Cheops, the Pyramid of Khafre, and the Pyramid of Menkaure. You will also see the Great Sphinx."
            },
            {
                "stop": "Cairo Lunch",
                "type": "Stop",
                "description": "Enjoy a freshly prepared lunch at a local restaurant in Cairo."
            },
            {
                "stop": "Cairo Optional",
                "type": "Stop",
                "description": "Optional stops such as a Nile River boat ride or shopping at a local bazaar may be available."
            },
            {
                "stop": "Cairo Airport Transfer",
                "type": "Pass By",
                "description": "Transfer to Cairo Airport for your return flight."
            },
            {
                "stop": "Return Flight",
                "type": "Stop",
                "description": "Flight from Cairo to Hurghada"
            },
            {
                "stop": "Hotel Drop-off",
                "type": "Stop",
                "description": "Late Evening – Hotel Drop-off in Marsa Alam."
            }
        ],
        "additional_info": [
            "Confirmation will be received at time of booking",
            "Not wheelchair accessible",
            "Infants must sit on laps",
            "Not recommended for pregnant travelers",
            "No heart problems or other serious medical conditions",
            "Most travelers can participate",
            "This is a small-group tour with maximum 15 travelers"
        ],
        "supplier": {
            "name": "FTS Travels",
            "rating": "TripAdvisor Reviews: 11"
        },
        "cancellation_policy": {
            "description": "You can cancel up to 24 hours in advance of the experience for a full refund.",
            "free_cancellation": "up to 24 hours before the experience starts (local time)"
        },
        "booking_options": {
            "reserve_now_pay_later": False,
            "reserve_now_pay_later_description": "Check availability"
        }
    },
    "14976P139": { 
       "tour_info": { 
         "platform": "Viator", 
         "url": "https://www.viator.com/tours/Hurghada/Hurghada-Cruise-to-Bianca-Island-Utopia-with-Transfer-and-Lunch/d800-14976P139", 
         "product_code": "14976P139", 
         "title": "Utopia - Bianca Island with Transfer and Lunch from Hurghada", 
         "location": "Hurghada, Egypt", 
         "category": "Snorkeling", 
         "breadcrumb": ["Home", "Things to do in Egypt", "Things to do in Red Sea", "Things to do in Hurghada", "Hurghada Tours", "On the Water", "Snorkeling"] 
       }, 
       "pricing": { 
         "price_from": 30.00, 
         "currency": "USD", 
         "price_unit": "per person", 
         "discounted_rates_for_kids": True, 
         "lowest_price_guarantee": True,
         "extra_charges": [ 
           { 
             "description": "Transportation El-Gouna, Shal Hasheesh, Qusseir with an extra charge", 
             "amount": 10.00, 
             "currency": "EUR"
           } 
         ]
       }, 
       "overview": { 
         "description": "Your day begins with a comfortable hotel pickup in Hurghada, followed by a relaxing cruise across the Red Sea toward the beautiful Bianca Island (Utopia). Enjoy stunning sea views as you sail, and stop at select snorkeling spots where you can explore vibrant coral reefs and colorful marine life with the guidance of the crew. Upon arrival at Bianca Island, you'll have free time to swim, sunbathe, or stroll along the pristine sandy beaches. Whether you want to unwind in a peaceful setting or enjoy snorkeling in shallow turquoise waters, the island offers the perfect escape. A freshly prepared lunch is included, giving you time to refuel and enjoy the moment before heading back to the boat.", 
         "highlights": [ 
           "Exclusive access to the beautiful and uncrowded Bianca Island Utopia", 
           "Ultra all-inclusive experience with unlimited drinks and buffet lunch", 
           "Combination of cruise, glass boat tour, water sports, and snorkeling", 
           "Family-friendly with kids' activities and professional supervision", 
           "Stunning scenery and photo-perfect beaches, ideal for relaxation" 
         ], 
         "duration": "8 hours (approx.)", 
         "start_time": "Varies (pickup 10-15 minutes before)", 
         "languages": ["English", "and 2 more"] 
       }, 
       "features": { 
         "pickup_offered": True, 
         "mobile_ticket": True, 
         "group_discounts": False, 
         "wheelchair_accessible": False, 
         "private_tour": False, 
         "max_travelers": 100 
       }, 
       "whats_included": [ 
         "Round-trip hotel transfer from Hurghada", 
         "Boat cruise to Bianca Island Utopia", 
         "Welcome drink on arrival", 
         "unlimited soft drinks, water & snacks", 
         "Glass-bottom boat tour", 
         "Water sports activities", 
         "Buffet lunch served on the island", 
         "1 Snorkeling stop including snorkeling equipment", 
         "Beach facilities including sunbeds & shaded areas", 
         "Kids' club activities (face painting, supervised games)", 
         "Sea food menu (Shrimps, Calamari & Fried fish)", 
         "Free Entrance to Bianca Island" 
       ], 
       "whats_not_included": [ 
         "Personal expenses", 
         "Towels (please bring your own)", 
         "Tips or gratuities for crew and staff", 
         "Transportation El-Gouna, Shal Hasheesh, Qusseir with an extra charge (€10.00 per person)" 
       ], 
       "meeting_and_pickup": { 
         "pickup_points": "Hurghada, Red Sea Governorate, Egypt", 
         "pickup_details": "Pickup is available from all hotels and resorts in Hurghada, including Sahl Hasheesh, Makadi Bay, and El Gouna (surcharges may apply for remote areas). Please be ready in your hotel lobby 10–15 minutes before your scheduled pickup time.", 
         "start_time": "Varies" 
       }, 
       "itinerary": [ 
         { 
           "stop": "Utopia Island", 
           "type": "Stop",
           "description": "Sail across the Red Sea to Bianca Island (Utopia), stopping at snorkeling spots to explore coral reefs. Upon arrival, enjoy swimming, sunbathing, water sports, and relaxation on pristine beaches."
         } 
       ], 
       "additional_info": [ 
         "Confirmation will be received at time of booking", 
         "Not wheelchair accessible", 
         "Not recommended for travelers with back problems", 
         "No heart problems or other serious medical conditions", 
         "Most travelers can participate", 
         "This tour/activity will have a maximum of 100 travelers", 
         "Family-friendly experience" 
       ], 
       "supplier": { 
         "name": "FTS Travels", 
         "rating": "TripAdvisor Reviews: 6220 (5.0 Stars)" 
       }, 
       "cancellation_policy": { 
         "description": "You can cancel up to 24 hours in advance of the experience for a full refund.", 
         "free_cancellation": "up to 24 hours before the experience starts (local time)" 
       }, 
       "booking_options": { 
         "reserve_now_pay_later": True, 
         "reserve_now_pay_later_description": "Secure your spot while staying flexible" 
       } 
    },
    "14976P138": { 
       "tour_info": { 
         "platform": "Viator", 
         "url": "https://www.viator.com/tours/Cairo/Luxor-Day-Trip-from-Cairo-by-Flight-Small-Group-Tour/d782-14976P138", 
         "product_code": "14976P138", 
         "title": "Luxor Small Group from Cairo by Plane: Tutankhamun Optional", 
         "location": "Cairo, Egypt", 
         "category": "Day Trips", 
         "breadcrumb": ["Home", "Things to do in Egypt", "Things to do in Cairo", "Cairo Tours", "Day Trips"] 
       }, 
       "pricing": { 
         "price_from": 100.00, 
         "currency": "USD", 
         "price_unit": "per person", 
         "discounted_rates_for_children": True, 
         "lowest_price_guarantee": True 
       }, 
       "overview": { 
         "description": "Private small-group experience avoiding large crowds with expert guide providing fascinating historical insights about ancient Egypt. Fast domestic flight from Cairo maximizes time in Luxor to see all top attractions in a single day.", 
         "highlights": [ 
           "Private small-group experience: Avoid large crowds and enjoy a more personalized tour", 
           "Fast domestic flight from Cairo: Maximize your time in Luxor and see all the top attractions in a single day", 
           "Expert guide: Learn fascinating historical insights about ancient Egypt", 
           "All major Luxor highlights included: Valley of the Kings, Temple of Hatshepsut, Colossi of Memnon, and Karnak Temple", 
           "Convenient hotel pickup & drop-off: Hassle-free transfers ensure a smooth, stress-free experience", 
           "Flexible tour pace: Optional extra tombs and free time to explore at your own pace", 
           "Comfort & convenience: Air-conditioned transport, bottled water" 
         ], 
         "duration": "14 hours (approx.)", 
         "start_time": "4:30 am", 
         "languages": ["English", "and 5 more"] 
       }, 
       "features": { 
         "pickup_offered": True, 
         "group_discounts": True, 
         "mobile_ticket": True, 
         "wheelchair_accessible": False, 
         "private_tour": False, 
         "small_group": True, 
         "max_travelers": 15 
       }, 
       "whats_included": [ 
         "Round-trip domestic flight from Cairo to Luxor", 
         "Pickup and drop-off at your Cairo hotel", 
         "Air-conditioned private transport in Luxor", 
         "Professional guide throughout the tour", 
         "Valley of the Kings (if selected)", 
         "Tutankhamun's tomb (if selected)", 
         "Temple of Hatshepsut (if selected)", 
         "Colossi of Memnon (if selected)", 
         "Karnak Temple (if selected)", 
         "Luxor Temple (if selected)", 
         "Lunch at a local restaurant", 
         "Bottled water during the tour" 
       ], 
       "whats_not_included": [ 
         "Personal expense", 
         "Optional tombs" 
       ], 
       "meeting_and_pickup": { 
         "pickup_points": "Select a pickup point", 
         "pickup_details": "The team will contact you one day before the tour to confirm the exact pickup time and flight details. Pickup is available from all hotels in Cairo and Giza only. Pickup time may vary depending on your hotel location and the domestic flight schedule. Please be in the hotel lobby 10 minutes before the confirmed time. If your accommodation is an apartment/Airbnb, we will arrange the nearest accessible meeting point. Please make sure to provide your full hotel name, room number, and an active WhatsApp number to ensure smooth coordination.", 
         "start_time": "4:30 am", 
         "pickup_areas": ["Cairo hotels", "Giza hotels"] 
       }, 
       "itinerary": [ 
         { "stop": "Cairo", "type": "Stop", "description": "Pickup from your Cairo hotel and transfer to Cairo Airport" },
         { "stop": "Cairo to Luxor", "type": "Stop", "description": "Flight from Cairo to Luxor" },
         { "stop": "Luxor Airport", "type": "Stop", "description": "Arrival in Luxor, meet your English-speaking guide and private transport" },
         { "stop": "Valley of the Kings", "type": "Stop", "description": "Visit the Valley of the Kings—explore several tombs" },
         { "stop": "Temple of Hatshepsut", "type": "Stop", "description": "Visit the Temple of Hatshepsut (Deir el-Bahari)" },
         { "stop": "Colossi of Memnon", "type": "Stop", "description": "Stop at the Colossi of Memnon – photo opportunity" },
         { "stop": "Luxor Lunch", "type": "Stop", "description": "Lunch break at a local restaurant (optional, not included)" },
         { "stop": "Temple of Karnak", "type": "Stop", "description": "Visit Karnak Temple Complex, explore the massive columns, obelisks, and sacred lake" },
         { "stop": "Luxor Temple", "type": "Stop", "description": "Visit Luxor Temple – admire the night-lit monument if time permits" },
         { "stop": "Luxor Airport", "type": "Stop", "description": "Transfer to Luxor Airport for the flight back to Cairo" },
         { "stop": "Cairo", "type": "Stop", "description": "Arrival in Cairo and drop-off at your hotel" }
       ], 
       "additional_info": [ 
         "Confirmation will be received at time of booking", 
         "Not wheelchair accessible", 
         "Not recommended for travelers with back problems", 
         "No heart problems or other serious medical conditions", 
         "Travelers should have a moderate physical fitness level", 
         "This tour/activity will have a maximum of 15 travelers", 
         "Small group experience for personalized service" 
       ], 
       "supplier": { 
         "name": "FTS Travels", 
         "rating": "TripAdvisor Reviews: 176 (5.0 Stars)" 
       }, 
       "cancellation_policy": { 
         "description": "You can cancel up to 24 hours in advance of the experience for a full refund.", 
         "free_cancellation": "up to 24 hours before the experience starts (local time)" 
       }, 
       "booking_options": { 
         "reserve_now_pay_later": True, 
         "reserve_now_pay_later_description": "Secure your spot while staying flexible" 
       } 
    },
    "14976P135": { 
       "tour_info": { 
         "platform": "Viator", 
         "url": "https://www.viator.com/tours/Hurghada/Hurghada-Private-Airport-Arrival-Departure-One-Way-Transfer/d800-14976P135", 
         "product_code": "14976P135", 
         "title": "Airport Private Transfer from Hurghada,Fast & Comfortable Service", 
         "location": "Hurghada, Egypt", 
         "category": "Airport & Hotel Transfers", 
         "breadcrumb": ["Home", "Things to do in Egypt", "Things to do in Hurghada", "Hurghada Tours", "Transfers", "Airport & Hotel Transfers"] 
       }, 
       "pricing": { 
         "price_from": 12.00, 
         "currency": "USD", 
         "price_unit": "per person", 
         "discounted_rates_for_kids": False, 
         "lowest_price_guarantee": True,
         "extra_charges": [ 
           { 
             "description": "Pickup service from Makadi, Sahl Hasheesh", 
             "amount": 10.00, 
             "currency": "EUR"
           }, 
           { 
             "description": "Pickup service from El-Gouna, Soma bay and Safaga", 
             "amount": 15.00, 
             "currency": "EUR"
           } 
         ]
       }, 
       "overview": { 
         "description": "Enjoy a personalized, private transfer with a professional English-speaking driver who ensures your comfort and safety. We provide flight tracking to adjust pickup times based on flight delays, so you never have to worry. Travel in a modern, air-conditioned vehicle with ample space for luggage. Your service offers clear communication before your trip, and we guarantee punctuality, ensuring timely arrivals at your hotel or the airport. Relax knowing we handle the details, giving you a stress-free experience from start to finish.", 
         "highlights": [ 
           "Private transportation with professional driver", 
           "Meet-and-greet service at Hurghada Airport or hotel", 
           "Flight tracking for arrival delays", 
           "Modern air-conditioned vehicle", 
           "Stress-free transfer to/from your destination" 
         ], 
         "duration": "1 hour (approx.)", 
         "start_time": "Flexible (Based on flight)", 
         "languages": ["English", "and 5 more"] 
       }, 
       "features": { 
         "pickup_offered": True, 
         "group_discounts": True, 
         "mobile_ticket": True, 
         "wheelchair_accessible": False, 
         "private_tour": True, 
         "small_group": False 
       }, 
       "whats_included": [ 
         "Private transportation", 
         "Professional driver", 
         "Meet-and-greet service at Hurghada Airport or hotel", 
         "Luggage assistance for smooth handling",
         "Flight tracking (for arrival transfers)" 
       ], 
       "whats_not_included": [ 
         "Tips (optional, based on your satisfaction)", 
         "Any extras not mentioned in the itinerary", 
         "Pickup service from Makadi, Sahl Hasheesh (€10.00 per person)", 
         "Pickup service from El-Gouna, Soma bay and Safaga (€15.00 per person)" 
       ], 
       "meeting_and_pickup": { 
         "pickup_points": "Select a pickup point", 
         "pickup_details": "Please provide your flight number, arrival or departure time, and hotel name in Hurghada when booking to ensure a smooth transfer. Our driver will be waiting for you at the airport arrival hall, holding a sign with your name, or at your hotel reception for departure transfers. For any assistance, please contact us via WhatsApp for faster coordination.", 
         "start_time": "Flexible", 
         "drop_off_point": "Hurghada International Airport or Hotel" 
       }, 
       "itinerary": [ 
         { "stop": "Booking & Confirmation", "type": "Info", "description": "Once you book, provide flight details for smooth process." },
         { "stop": "Pre-Trip Communication", "type": "Info", "description": "We will contact you via email/WhatsApp to confirm pickup details." },
         { "stop": "Arrival/Pickup", "type": "Stop", "description": "Driver waits at Airport arrival hall or Hotel reception with a sign." },
         { "stop": "Transfer", "type": "Stop", "description": "Comfortable ride in air-conditioned vehicle to your destination." },
         { "stop": "Drop-Off", "type": "Stop", "description": "Drop-off at hotel lobby or airport departure hall." } 
       ], 
       "additional_info": [ 
         "Confirmation will be received at time of booking", 
         "Not wheelchair accessible", 
         "Most travelers can participate", 
         "This is a private tour/activity. Only your group will participate" 
       ], 
       "supplier": { 
         "name": "FTS Travels", 
         "rating": "TripAdvisor Reviews: 1 (5.0 Stars)" 
       }, 
       "cancellation_policy": { 
         "description": "You can cancel up to 24 hours in advance of the experience for a full refund.", 
         "free_cancellation": "up to 24 hours before the experience starts (local time)" 
       }, 
       "booking_options": { 
         "reserve_now_pay_later": True, 
         "reserve_now_pay_later_description": "Secure your spot while staying flexible" 
       } 
    },
    "14976P3": { 
       "tour_info": { 
         "platform": "Viator", 
         "url": "https://www.viator.com/tours/Hurghada/Day-Tour-to-Luxor-from-Hurghada-by-Car/d800-14976P3", 
         "product_code": "14976P3", 
         "title": "Hurghada: Luxor Valley of the Kings & Tutankhamun Tomb Trip", 
         "location": "Hurghada, Egypt", 
         "category": "Day Trips", 
         "breadcrumb": ["Home", "Things to do in Egypt", "Things to do in Hurghada", "Hurghada Tours", "Day Trips"] 
       }, 
       "pricing": { 
         "price_from": 35.72, 
         "currency": "USD", 
         "price_unit": "per person", 
         "discounted_rates_for_kids": True, 
         "lowest_price_guarantee": True 
       }, 
       "overview": { 
         "description": "Step back in time with a full-day guided tour of Luxor's ancient tombs and treasures from Hurghada. Stroll between two great lines of sphinxes as you enter Karnak Temple to see the buildings and sacred lake within the complex. Pause for lunch at a local restaurant then visit the Valley of the Kings' royal tombs and Queen Hatshepsut's vast temple before returning to your hotel. Upgrade to include entrance fees.", 
         "highlights": [ 
           "Tour Luxor's ancient sites from Hurghada in a group of maximum 15", 
           "Visit Karnak Temple, the Valley of the Kings, and more", 
           "Includes 2-way transfers from Hurghada and Makadi hotels plus lunch", 
           "Comfortable air-conditioned transport", 
           "Guided by an expert Egyptologist" 
         ], 
         "duration": "15 to 16 hours (approx.)", 
         "start_time": "4:00 am", 
         "languages": ["English", "and 6 more"] 
       }, 
       "features": { 
         "pickup_offered": True, 
         "group_discounts": True, 
         "mobile_ticket": True, 
         "wheelchair_accessible": False, 
         "private_tour": False, 
         "small_group": True, 
         "max_travelers": 15 
       }, 
       "whats_included": [ 
         "All transfers by an air-conditioned vehicle", 
         "A bottle of Mineral water during your trip", 
         "All taxes & services charge", 
         "Egyptologist guide", 
         "Lunch at local restaurant" 
       ], 
       "whats_not_included": [ 
         "Drinks in the restaurant", 
         "Optional 20-minute cruise (10 EUR)", 
         "Pickup surcharge for Al-Ahyaa, El Gouna, Sahl Hasheesh, Safaga, Soma Bay (€10.00)", 
         "Entrance fees (unless option selected)" 
       ], 
       "meeting_and_pickup": { 
         "pickup_points": "Select a pickup point", 
         "pickup_details": "Important Things to Bring: Original passport (mandatory). Light clothing, hat, and sun protection. Pickup starts around 4:00 AM.", 
         "start_time": "4:00 am" 
       }, 
       "itinerary": [ 
         { "stop": "Hurghada to Luxor", "type": "Stop", "description": "Drive from Hurghada to Luxor through the desert/mountains." },
         { "stop": "Temple of Karnak", "type": "Stop", "description": "Visit Egypt's most famous monuments, including the Temple of Karnak and Sacred Lake." },
         { "stop": "Luxor Lunch", "type": "Stop", "description": "Relax over lunch at a local restaurant. Optional Nile crossing by boat." },
         { "stop": "Colossi of Memnon", "type": "Stop", "description": "See the impressive Colossi of Memnon statues." },
         { "stop": "Temple of Hatshepsut", "type": "Stop", "description": "Visit the temple of Hatshepsut at Deir el Bahari." },
         { "stop": "Valley of the Kings", "type": "Stop", "description": "Explore the royal tombs where King Tutankhamun was found." },
         { "stop": "Return to Hurghada", "type": "Stop", "description": "Drive back to your hotel in Hurghada." } 
       ], 
       "additional_info": [ 
         "Confirmation will be received at time of booking", 
         "Not wheelchair accessible", 
         "Not recommended for travelers with back problems", 
         "Travelers should have a moderate physical fitness level", 
         "Original passport required", 
         "No large luggage allowed on bus" 
       ], 
       "supplier": { 
         "name": "FTS Travels", 
         "rating": "TripAdvisor Reviews: 3,745 (4.8 Stars)" 
       }, 
       "cancellation_policy": { 
         "description": "You can cancel up to 24 hours in advance of the experience for a full refund.", 
         "free_cancellation": "up to 24 hours before the experience starts (local time)" 
       }, 
       "booking_options": { 
         "reserve_now_pay_later": True, 
         "reserve_now_pay_later_description": "Secure your spot while staying flexible" 
       } 
     },
    "14976P7": { 
       "tour_info": { 
         "platform": "Viator", 
         "url": "https://www.viator.com/tours/Hurghada/Full-Day-Tour-Hurghada-to-Cairo-by-Bus/d800-14976P7", 
         "product_code": "14976P7", 
         "title": "From Hurghada Legacy Trip–Explore Cairo's Pyramids & Grand Museum", 
         "location": "Hurghada, Egypt", 
         "category": "Full-day Tours", 
         "breadcrumb": ["Home", "Things to do in Egypt", "Things to do in Hurghada", "Hurghada Tours", "Full-day Tours"] 
       }, 
       "pricing": { 
         "price_from": 35.00, 
         "currency": "USD", 
         "price_unit": "per person", 
         "discounted_rates_for_kids": True, 
         "lowest_price_guarantee": True 
       }, 
       "overview": { 
         "description": "This Cairo and Giza private full-day highlights tour from Hurghada is ideal for those who want to see key attractions but only have a day to spare during their time in Egypt. Plus, along with round-trip transport from Hurghada, lunch and a private Egyptologist guide are included, too. See the Egyptian Museum in Cairo, the Giza Pyramids, and more. You can also add a Nile River cruise when you book.", 
         "highlights": [ 
           "Explore Cairo and Giza highlights in just one day", 
           "A private Egyptologist guide makes the most out of your time in Egypt", 
           "Choose to book an all-include tour option or pay for attraction admission later", 
           "Pick a tour option with a Nile cruise upgrade or Great Pyramid visit", 
           "Comfortable air-conditioned bus transport" 
         ], 
         "duration": "18 hours (approx.)", 
         "start_time": "1:30 am", 
         "languages": ["English", "and 5 more"] 
       }, 
       "features": { 
         "pickup_offered": True, 
         "group_discounts": True, 
         "mobile_ticket": True, 
         "wheelchair_accessible": False, 
         "private_tour": False, 
         "small_group": False, 
         "max_travelers": 200 
       }, 
       "whats_included": [ 
         "Hotel pickup and drop-off in Hurghada", 
         "Air-conditioned vehicle for transfers", 
         "Professional Egyptologist tour guide" 
       ], 
       "whats_not_included": [ 
         "Tips", 
         "Any other personal expenses", 
         "Drinks at the restaurant", 
         "Pickup surcharge for remote areas (Makadi, Sahl Hasheesh, El Gouna, etc.)" 
       ], 
       "meeting_and_pickup": { 
         "pickup_points": "Select a pickup point", 
         "pickup_details": "Pickup is included from all hotels in Hurghada. For hotels located in Makadi Bay, Sahl Hasheesh, El Gouna, Safaga, or Soma Bay, an additional transfer fee may apply. Exact pickup times will be confirmed after booking based on your hotel location.", 
         "start_time": "1:30 am" 
       }, 
       "itinerary": [ 
         { "stop": "Hurghada to Cairo", "type": "Stop", "description": "Pickup from hotels in Hurghada (00:30–03:00) and drive to Cairo." },
         { "stop": "Arrival in Cairo", "type": "Pass By", "description": "Meet your Egyptologist guide upon arrival." },
         { "stop": "The Egyptian Museum in Cairo", "type": "Stop", "description": "Begin your journey at the world-famous Egyptian Museum in Tahrir Square. Discover thousands of ancient treasures." },
         { "stop": "Lunch", "type": "Stop", "description": "Buffet lunch with authentic Egyptian cuisine." },
         { "stop": "Great Sphinx", "type": "Stop", "description": "Stand face to face with the legendary Sphinx." },
         { "stop": "Pyramids of Giza", "type": "Stop", "description": "Visit one of the Seven Wonders of the Ancient World. Marvel at the Great Pyramid of Khufu." },
         { "stop": "Workshops", "type": "Pass By", "description": "Visit authentic local workshops (Papyrus & Perfume). Shopping is optional." },
         { "stop": "Return to Hurghada", "type": "Stop", "description": "Depart from Cairo and start the journey back to Hurghada." } 
       ], 
       "additional_info": [ 
         "Confirmation will be received at time of booking", 
         "Not wheelchair accessible", 
         "Infant seats available", 
         "Most travelers can participate", 
         "The tour is available from hotels in Elgouna, Hurghada, Sahl Hashish, Makadi, and Safaga", 
         "This tour/activity will have a maximum of 200 travelers" 
       ], 
       "supplier": { 
         "name": "FTS Travels", 
         "rating": "TripAdvisor Reviews: 562 (4.8 Stars)" 
       }, 
       "cancellation_policy": { 
         "description": "You can cancel up to 24 hours in advance of the experience for a full refund.", 
         "free_cancellation": "up to 24 hours before the experience starts (local time)" 
       }, 
       "booking_options": { 
         "reserve_now_pay_later": True, 
         "reserve_now_pay_later_description": "Secure your spot while staying flexible" 
       } 
     },
    "14976P133": { 
       "tour_info": { 
         "platform": "Viator", 
         "url": "https://www.viator.com/tours/Hurghada/Hurghada-2-Day-Private-Tour-of-Luxor-and-Abu-Simbel/d800-14976P133", 
         "product_code": "14976P133", 
         "title": "Luxor and Abu Simbel 2-Day Private Tour from Hurghada", 
         "location": "Hurghada, Egypt", 
         "category": "Multi-day Tours", 
         "breadcrumb": ["Home", "Things to do in Egypt", "Things to do in Hurghada", "Hurghada Tours", "Multi-day Tours"] 
       }, 
       "pricing": { 
         "price_from": 500.00, 
         "currency": "USD", 
         "price_unit": "per person", 
         "discounted_rates_for_kids": True, 
         "lowest_price_guarantee": True 
       }, 
       "overview": { 
         "description": "Exclusive private experience – Travel at your own pace with a dedicated Egyptologist guide. Two iconic destinations in one trip – Discover the treasures of Luxor and the majestic Abu Simbel in just 2 days. Comfort & convenience – Enjoy private transfers in a modern, air-conditioned vehicle and a carefully planned itinerary that maximizes your time.", 
         "highlights": [ 
           "Exclusive private experience – Travel at your own pace", 
           "Two iconic destinations in one trip – Luxor and Abu Simbel", 
           "Comfort & convenience – Private air-conditioned transfers", 
           "Personalized storytelling – Expert insights", 
           "Hassle-free journey – Entrance fees and meals included" 
         ], 
         "duration": "2 days (approx.)", 
         "start_time": "4:30 AM", 
         "languages": ["English", "and 4 more"] 
       }, 
       "features": { 
         "pickup_offered": True, 
         "group_discounts": True, 
         "mobile_ticket": True, 
         "wheelchair_accessible": False, 
         "private_tour": True, 
         "small_group": False 
       }, 
       "whats_included": [ 
         "Lunch", 
         "Breakfast", 
         "Private transportation", 
         "Professional Egyptologist guide",
         "Entrance fees to mentioned sites" 
       ], 
       "whats_not_included": [ 
         "Drinks during meals", 
         "Personal expenses", 
         "Optional activities or extras not mentioned in the itinerary", 
         "Accommodation (Not included)" 
       ], 
       "meeting_and_pickup": { 
         "pickup_points": "Select a pickup point", 
         "pickup_details": "Pickup is available from all hotels and resorts in Hurghada. Please be ready in the hotel lobby 10 minutes before your scheduled pickup time. Exact pickup time will be confirmed one day before the tour via email or phone. Transfers are provided in air-conditioned vehicles for your comfort", 
         "start_time": "4:30 AM" 
       }, 
       "itinerary": [ 
         { "stop": "Hurghada to Luxor", "type": "Stop", "description": "Pickup from your hotel in Hurghada in a private air-conditioned vehicle." },
         { "stop": "Temple of Karnak", "type": "Stop", "description": "Explore the largest religious structure ever built, dedicated to Amun-Ra." },
         { "stop": "Luxor Lunch", "type": "Stop", "description": "Enjoy traditional Egyptian cuisine at a local restaurant." },
         { "stop": "Valley of the Kings", "type": "Stop", "description": "Visit the royal tombs of the New Kingdom Pharaohs." },
         { "stop": "Temple of Hatshepsut", "type": "Stop", "description": "Marvel at the terraced temple of Egypt's famous female pharaoh." },
         { "stop": "Colossi of Memnon", "type": "Stop", "description": "Short photo stop at the two giant statues of Amenhotep III." },
         { "stop": "Drive to Aswan", "type": "Stop", "description": "Drive along the Nile valley to Aswan for overnight stay (accommodation not included)." },
         { "stop": "Abu Simbel", "type": "Stop", "description": "Transfer from Aswan to Abu Simbel. Admire the monumental rock-cut temples." },
         { "stop": "Return to Hurghada", "type": "Stop", "description": "Transfer back to your hotel in Hurghada." } 
       ], 
       "additional_info": [ 
         "Confirmation will be received at time of booking", 
         "Not wheelchair accessible", 
         "Not recommended for travelers with back problems", 
         "No heart problems or other serious medical conditions", 
         "Most travelers can participate", 
         "This is a private tour/activity. Only your group will participate" 
       ], 
       "supplier": { 
         "name": "FTS Travels", 
         "rating": "TripAdvisor Reviews: 2 (4.5 Stars)" 
       }, 
       "cancellation_policy": { 
         "description": "You can cancel up to 24 hours in advance of the experience for a full refund.", 
         "free_cancellation": "up to 24 hours before the experience starts (local time)" 
       }, 
       "booking_options": { 
         "reserve_now_pay_later": True, 
         "reserve_now_pay_later_description": "Secure your spot while staying flexible" 
       } 
     },
    "14976P131": { 
       "tour_info": { 
         "platform": "Viator", 
         "url": "https://www.viator.com/tours/Hurghada/Hurghada-2-Day-Luxor-Tour-with-Hotel-Balloon-and-Nile-Boat/d800-14976P131", 
         "product_code": "14976P131", 
         "title": "Luxor Tour 2-Day with Hotel, Balloon, & Nile Boat - Hurghada", 
         "location": "Hurghada, Egypt", 
         "category": "Multi-day Tours", 
         "breadcrumb": ["Home", "Things to do in Egypt", "Things to do in Hurghada", "Hurghada Tours", "Multi-day Tours"] 
       }, 
       "pricing": { 
         "price_from": 200.00, 
         "currency": "USD", 
         "price_unit": "per person", 
         "discounted_rates_for_kids": True, 
         "lowest_price_guarantee": True 
       }, 
       "overview": { 
         "description": "Discover the wonders of Luxor on this unique 2-day tour from Hurghada. Unlike rushed day trips, this experience gives you time to fully explore both the East and West Banks of the Nile. Marvel at the vast Karnak Temple and elegant Luxor Temple, then cross the Nile for the royal tombs in the Valley of the Kings, the stunning Temple of Hatshepsut, and the towering Colossi of Memnon. Sunrise hot air balloon ride offering breathtaking views of Luxor from above.", 
         "highlights": [ 
           "2-day tour from Hurghada with 4-star hotel stay", 
           "Sunrise hot air balloon ride included", 
           "Explore East and West Banks of Luxor", 
           "Nile boat ride included", 
           "Private transfers and Egyptologist guide" 
         ], 
         "duration": "2 days (approx.)", 
         "start_time": "4:30 AM", 
         "languages": ["English", "and 4 more"] 
       }, 
       "features": { 
         "pickup_offered": True, 
         "group_discounts": True, 
         "mobile_ticket": True, 
         "wheelchair_accessible": False, 
         "private_tour": True, 
         "small_group": False 
       }, 
       "whats_included": [ 
         "Pickup and drop-off from your hotel in Hurghada", 
         "Dinner", 
         "Breakfast", 
         "Lunch", 
         "4-star hotel accommodation in Luxor (Day 1)", 
         "Hot air balloon ride", 
         "Nile boat ride", 
         "Private air-conditioned vehicle", 
         "Professional Egyptologist guide", 
         "All entrance fees to mentioned sites" 
       ], 
       "whats_not_included": [ 
         "Tips", 
         "Personal expenses", 
         "Drinks at restaurants" 
       ], 
       "meeting_and_pickup": { 
         "pickup_points": "Select a pickup point", 
         "pickup_details": "Pickup is available from all hotels and resorts in Hurghada. Please be ready in the hotel lobby 10 minutes before your scheduled pickup time. Exact pickup time will be confirmed one day before the tour via email or phone. Transfers are provided in air-conditioned vehicles for your comfort", 
         "start_time": "4:30 AM" 
       }, 
       "itinerary": [ 
         { "stop": "Hurghada to Luxor", "type": "Stop", "description": "Early morning pickup from your Hurghada hotel. Travel to Luxor and begin exploring the East Bank." },
         { "stop": "Temple of Karnak", "type": "Stop", "description": "Walk along the Avenue of Sphinxes and enter the Great Hypostyle Hall." },
         { "stop": "Luxor Hotel", "type": "Stop", "description": "Check into your 4-star hotel in Luxor and enjoy dinner. Evening at leisure." },
         { "stop": "Hot Air Balloon", "type": "Stop", "description": "Sunrise hot air balloon ride over Luxor offering breathtaking views." },
         { "stop": "Valley of the Kings", "type": "Stop", "description": "Explore the royal burial ground of the New Kingdom pharaohs." },
         { "stop": "Temple of Hatshepsut", "type": "Stop", "description": "Witness one of the most impressive architectural masterpieces at Deir el-Bahari." },
         { "stop": "Colossi of Memnon", "type": "Stop", "description": "See the two massive stone statues on the west bank." },
         { "stop": "Return to Hurghada", "type": "Stop", "description": "Transfer back to your hotel in Hurghada." } 
       ], 
       "additional_info": [ 
         "Confirmation will be received at time of booking", 
         "Not wheelchair accessible", 
         "Not recommended for travelers with back problems", 
         "No heart problems or other serious medical conditions", 
         "Most travelers can participate", 
         "This is a private tour/activity. Only your group will participate" 
       ], 
       "supplier": { 
         "name": "FTS Travels", 
         "rating": "TripAdvisor Reviews: 6220 (Operator)" 
       }, 
       "cancellation_policy": { 
         "description": "You can cancel up to 24 hours in advance of the experience for a full refund.", 
         "free_cancellation": "up to 24 hours before the experience starts (local time)" 
       }, 
       "booking_options": { 
         "reserve_now_pay_later": True, 
         "reserve_now_pay_later_description": "Secure your spot while staying flexible" 
       } 
     },
    "14976P129": { 
       "tour_info": { 
         "platform": "Viator", 
         "url": "https://www.viator.com/tours/Hurghada/Full-Day-Tour-to-Abydos-Osireion-and-Dendera-from-Hurghada/d800-14976P129", 
         "product_code": "14976P129", 
         "title": "Dendera, Osireion & Abydos Full-Day Tour from Hurghada", 
         "location": "Hurghada, Egypt", 
         "category": "Full-day Tours", 
         "breadcrumb": ["Home", "Things to do in Egypt", "Things to do in Hurghada", "Hurghada Tours", "Full-day Tours"] 
       }, 
       "pricing": { 
         "price_from": 100.00, 
         "currency": "USD", 
         "price_unit": "per person", 
         "discounted_rates_for_kids": True, 
         "lowest_price_guarantee": True 
       }, 
       "overview": { 
         "description": "Explore the ancient archaeological wonders of Abydos and Dendera on this full-day tour from Hurghada. Uncover the secrets of the Osireion and the significance of the goddess Hathor at the Temple of Dendera, renowned for its well-preserved architecture and intricate astronomical carvings. Accompanied by an expert Egyptologist guide, delve into the rich history of ancient pharaohs.", 
         "highlights": [ 
           "Full-day private tour from Hurghada to Abydos and Dendera", 
           "Guided visits to the Temple of Dendera and the Osireion", 
           "Temple of Dendera renowned for astronomical carvings", 
           "Enjoy a delicious lunch at a local restaurant", 
           "Includes hotel pickup and drop-off for a seamless experience" 
         ], 
         "duration": "12 to 14 hours (approx.)", 
         "start_time": "4:30 AM", 
         "languages": ["English", "and 5 more"] 
       }, 
       "features": { 
         "pickup_offered": True, 
         "group_discounts": True, 
         "mobile_ticket": True, 
         "wheelchair_accessible": False, 
         "private_tour": False, 
         "small_group": False, 
         "max_travelers": 50 
       }, 
       "whats_included": [ 
         "Round-trip hotel transfers from Hurghada", 
         "Professional English-speaking guide", 
         "Entrance fees to Abydos, Osireion, and Dendera temples", 
         "Lunch" 
       ], 
       "whats_not_included": [ 
         "Personal expenses", 
         "Pickup and drop-off from Sahl Hasheesh, El Gouna, Soma Bay ($10.00 per person extra)", 
         "Tips" 
       ], 
       "meeting_and_pickup": { 
         "pickup_points": "Select a pickup point", 
         "pickup_details": "Pickup is available from Hurghada hotels. Please be ready in the hotel lobby 10 minutes before the scheduled pickup time. Exact pickup time will be confirmed 24 hours in advance via email or phone", 
         "start_time": "4:30 AM" 
       }, 
       "itinerary": [ 
         { "stop": "Hurghada to Abydos", "type": "Stop", "description": "Travel from Hurghada to Abydos." },
         { "stop": "Temple of Abydos", "type": "Stop", "description": "Visit the Temple of Seti I, famous for its detailed hieroglyphs and the Osiris Wall." },
         { "stop": "Osireion", "type": "Stop", "description": "Explore the mysterious underground structure linked to the god Osiris." },
         { "stop": "Dendera Temple", "type": "Stop", "description": "Visit the Temple of Hathor, known for its astronomical ceiling." },
         { "stop": "Lunch", "type": "Stop", "description": "Enjoy a delicious lunch at a local restaurant." },
         { "stop": "Return to Hurghada", "type": "Stop", "description": "Transfer back to your hotel in Hurghada." } 
       ], 
       "additional_info": [ 
         "Confirmation will be received at time of booking", 
         "Not wheelchair accessible", 
         "Not recommended for travelers with back problems", 
         "No heart problems or other serious medical conditions", 
         "Travelers should have a moderate physical fitness level", 
         "This tour/activity will have a maximum of 50 travelers" 
       ], 
       "supplier": { 
         "name": "FTS Travels", 
         "rating": "TripAdvisor Reviews: 2 (4.5 Stars)" 
       }, 
       "cancellation_policy": { 
         "description": "You can cancel up to 24 hours in advance of the experience for a full refund.", 
         "free_cancellation": "up to 24 hours before the experience starts (local time)" 
       }, 
       "booking_options": { 
         "reserve_now_pay_later": True, 
         "reserve_now_pay_later_description": "Secure your spot while staying flexible" 
       } 
     },
    "14976P127": { 
       "tour_info": { 
         "platform": "Viator", 
         "url": "https://www.viator.com/tours/Marsa-Alam/Snorkeling-Adventure-in-Marsa-Mubarak-Bay/d25556-14976P127", 
         "product_code": "14976P127", 
         "title": "Sea Turtles Marsa Mubarak, Boat trip with Snorkeling-Marsa Alam", 
         "location": "Marsa Alam, Egypt", 
         "category": "Snorkeling", 
         "breadcrumb": ["Home", "Things to do in Egypt", "Things to do in Red Sea", "Things to do in Marsa Alam", "Marsa Alam Tours", "Snorkeling"] 
       }, 
       "pricing": { 
         "price_from": 25.00, 
         "currency": "USD", 
         "price_unit": "per person", 
         "discounted_rates_for_kids": True, 
         "lowest_price_guarantee": True 
       }, 
       "overview": { 
         "description": "Your adventure begins with a comfortable transfer to the marina, where you'll board a boat and cruise to the famous Marsa Mubarak Bay. Once there, you'll dive into the crystal-clear waters for guided snorkeling sessions. Swim alongside majestic sea turtles, discover vibrant coral reefs, and admire a variety of colorful Red Sea fish. With a bit of luck, you may even spot the rare dugong grazing on sea grass. Between snorkeling stops, relax on deck, soak up the sun, and enjoy a delicious lunch prepared on board before returning to Marsa Alam.", 
         "highlights": [ 
           "Explore the vibrant underwater landscape of Marsa Mubarak", 
           "Swimming with gentle sea turtles and chance to see the dugong", 
           "Immerse yourself in crystal-clear waters with tropical fish", 
           "Boat transfers, snorkeling gear, and lunch provided", 
           "Experienced instructor to guide you", 
           "Caters to both novice and seasoned snorkelers" 
         ], 
         "duration": "7 hours (approx.)", 
         "start_time": "Varies", 
         "languages": ["English", "and 2 more"] 
       }, 
       "features": { 
         "pickup_offered": True, 
         "group_discounts": True, 
         "mobile_ticket": True, 
         "wheelchair_accessible": False, 
         "private_tour": False, 
         "small_group": False, 
         "max_travelers": 100 
       }, 
       "whats_included": [ 
         "Hotel pickup and drop-off from Marsa Alam", 
         "Boat trip to Marsa Mubarak Bay", 
         "2 guided snorkeling sessions", 
         "Snorkeling equipment", 
         "Lunch on board", 
         "Professional snorkeling instructor" 
       ], 
       "whats_not_included": [ 
         "Personal expenses", 
         "National park entrance fee (€7.00 per person, paid in cash on site)", 
         "Pickup from North Marsa Alam (€10.00 per person extra)", 
         "Tips" 
       ], 
       "meeting_and_pickup": { 
         "pickup_points": "Select a pickup point", 
         "pickup_details": "Pickup is available from all hotels in Marsa Alam. Please wait in the hotel lobby at least 10 minutes before your scheduled pickup time. Exact pickup time will be confirmed after booking, depending on your hotel location", 
         "start_time": "Varies" 
       }, 
       "itinerary": [ 
         { "stop": "Marsa Alam to Marina", "type": "Stop", "description": "Transfer to the marina." },
         { "stop": "Boat Cruise", "type": "Stop", "description": "Cruise to Marsa Mubarak Bay." },
         { "stop": "Snorkeling Session 1", "type": "Stop", "description": "Guided snorkeling session to see turtles and reefs." },
         { "stop": "Lunch", "type": "Stop", "description": "Delicious lunch prepared on board." },
         { "stop": "Snorkeling Session 2", "type": "Stop", "description": "Second snorkeling session." },
         { "stop": "Return to Marsa Alam", "type": "Stop", "description": "Cruise back to marina and transfer to hotel." } 
       ], 
       "additional_info": [ 
         "Confirmation will be received at time of booking", 
         "Not wheelchair accessible", 
         "Not recommended for travelers with back problems", 
         "No heart problems or other serious medical conditions", 
         "Most travelers can participate", 
         "This tour/activity will have a maximum of 100 travelers" 
       ], 
       "supplier": { 
         "name": "FTS Travels", 
         "rating": "TripAdvisor Reviews: 5 (4.5 Stars)" 
       }, 
       "cancellation_policy": { 
         "description": "You can cancel up to 24 hours in advance of the experience for a full refund.", 
         "free_cancellation": "up to 24 hours before the experience starts (local time)" 
       }, 
       "booking_options": { 
         "reserve_now_pay_later": True, 
         "reserve_now_pay_later_description": "Secure your spot while staying flexible" 
       } 
     },
    "14976P126": { 
       "tour_info": { 
         "platform": "Viator", 
         "url": "https://www.viator.com/tours/Marsa-Alam/Marsa-Alam-Snorkeling-Adventure-at-Shaab-Samadai-Reef/d25556-14976P126", 
         "product_code": "14976P126", 
         "title": "Shaab Samadai, Snorkeling Adventure & Coral Reef at Marsa Alam", 
         "location": "Marsa Alam, Egypt", 
         "category": "Snorkeling", 
         "breadcrumb": ["Home", "Things to do in Egypt", "Things to do in Red Sea", "Things to do in Marsa Alam", "Marsa Alam Tours", "Snorkeling"] 
       }, 
       "pricing": { 
         "price_from": 35.00, 
         "currency": "USD", 
         "price_unit": "per person", 
         "discounted_rates_for_kids": True, 
         "lowest_price_guarantee": True 
       }, 
       "overview": { 
         "description": "Start your day with a comfortable transfer from your hotel to the marina, where you'll board a boat bound for the famous Shaab Samadai Reef, also called Dolphin House. As you cruise across the Red Sea, enjoy the sea breeze and look out for playful spinner dolphins. Upon arrival, you'll have the chance to snorkel in crystal-clear waters, discovering vibrant coral gardens and colorful tropical fish. With a bit of luck, you may encounter dolphins swimming freely in their natural environment. Between snorkeling sessions, relax on deck, soak up the sun, and enjoy a delicious lunch prepared on board before returning to Marsa Alam.", 
         "highlights": [ 
           "Discover the beauty of Shaab Samadai Reef (Dolphin House)", 
           "Cruise the magnificent Red Sea and look for spinner dolphins", 
           "Dive into vibrant coral reefs filled with colorful fish", 
           "Freshly prepared lunch and refreshments on board", 
           "Opportunity to swim alongside wild dolphins", 
           "Convenient transfers from your Marsa Alam hotel are included" 
         ], 
         "duration": "7 hours (approx.)", 
         "start_time": "7:00 AM", 
         "languages": ["English", "and 2 more"] 
       }, 
       "features": { 
         "pickup_offered": True, 
         "group_discounts": True, 
         "mobile_ticket": True, 
         "wheelchair_accessible": False, 
         "private_tour": False, 
         "small_group": False, 
         "max_travelers": 100 
       }, 
       "whats_included": [ 
         "Hotel pickup and drop-off from Marsa Alam", 
         "Boat trip to Shaab Samadai Reef (Dolphin House)", 
         "2 guided snorkeling stops with equipment provided (mask, snorkel, fins)", 
         "Lunch on board", 
         "Soft drinks and refreshments", 
         "Professional snorkeling guide" 
       ], 
       "whats_not_included": [ 
         "Gratuities (optional)", 
         "Personal expenses", 
         "National park entrance fee (€7.00 per person, to be paid on-site)" 
       ], 
       "meeting_and_pickup": { 
         "pickup_points": "Select a pickup point", 
         "pickup_details": "Pickup is available from all hotels in Marsa Alam. Please wait in the hotel lobby or at the main entrance 10 minutes before your scheduled pickup time. The exact pickup time will be confirmed after booking, depending on your hotel location", 
         "start_time": "7:00 AM" 
       }, 
       "itinerary": [ 
         { "stop": "Marsa Alam to Marina", "type": "Stop", "description": "Transfer to the marina." },
         { "stop": "Boat Cruise", "type": "Stop", "description": "Cruise to Shaab Samadai Reef (Dolphin House)." },
         { "stop": "Snorkeling Stop 1", "type": "Stop", "description": "Guided snorkeling to explore coral reefs and marine life." },
         { "stop": "Lunch", "type": "Stop", "description": "Delicious lunch served on board." },
         { "stop": "Snorkeling Stop 2", "type": "Stop", "description": "Second snorkeling session, chance to see dolphins." },
         { "stop": "Return to Marsa Alam", "type": "Stop", "description": "Cruise back to marina and transfer to hotel." } 
       ], 
       "additional_info": [ 
         "Confirmation will be received at time of booking", 
         "Not wheelchair accessible", 
         "Not recommended for travelers with back problems", 
         "No heart problems or other serious medical conditions", 
         "Most travelers can participate", 
         "This tour/activity will have a maximum of 100 travelers" 
       ], 
       "supplier": { 
         "name": "FTS Travels", 
         "rating": "TripAdvisor Reviews: 1 (5.0 Stars)" 
       }, 
       "cancellation_policy": { 
         "description": "You can cancel up to 24 hours in advance of the experience for a full refund.", 
         "free_cancellation": "up to 24 hours before the experience starts (local time)" 
       }, 
       "booking_options": { 
         "reserve_now_pay_later": True, 
         "reserve_now_pay_later_description": "Secure your spot while staying flexible" 
       } 
     },
    "14976P125": { 
       "tour_info": { 
         "platform": "Viator", 
         "url": "https://www.viator.com/tours/Marsa-Alam/Marsa-Alam-Valley-of-the-Kings-and-Karnak-Temples-Luxor-Tour/d25556-14976P125", 
         "product_code": "14976P125", 
         "title": "Luxor Tour to Valley of the Kings, Karnak Temples from Marsa Alam", 
         "location": "Marsa Alam, Egypt", 
         "category": "Day Trips", 
         "breadcrumb": ["Home", "Things to do in Egypt", "Things to do in Red Sea", "Things to do in Marsa Alam", "Marsa Alam Tours", "Day Trips"] 
       }, 
       "pricing": { 
         "price_from": 75.00, 
         "currency": "USD", 
         "price_unit": "per person", 
         "discounted_rates_for_kids": True, 
         "lowest_price_guarantee": True 
       }, 
       "overview": { 
         "description": "Unlike standard group tours, this experience is crafted for comfort and depth. Travel in a private, air-conditioned vehicle with a professional Egyptologist who brings history to life at every site. Explore not only the world-famous Valley of the Kings and Karnak Temple but also Tutankhamun's Tomb (with extra fees), Hatshepsut's Temple, and the Colossi of Memnon — all in one day. With skip-the-line arrangements, personalized attention, and an authentic local lunch included, this tour ensures you see the highlights of Luxor with ease and exclusivity.", 
         "highlights": [ 
           "Travel in a private, air-conditioned vehicle", 
           "Professional Egyptologist tour guide", 
           "Visit Valley of the Kings and Karnak Temple", 
           "See Tutankhamun's Tomb (with extra fees)", 
           "Visit Hatshepsut's Temple and Colossi of Memnon", 
           "Skip-the-line arrangements", 
           "Authentic local lunch included" 
         ], 
         "duration": "16 to 17 hours (approx.)", 
         "start_time": "2:30 AM", 
         "languages": ["English", "and 6 more"] 
       }, 
       "features": { 
         "pickup_offered": True, 
         "group_discounts": True, 
         "mobile_ticket": True, 
         "wheelchair_accessible": False, 
         "private_tour": True, 
         "small_group": False, 
         "max_travelers": 100 
       }, 
       "whats_included": [ 
         "Hotel pickup and drop-off in Marsa Alam", 
         "Air-conditioned vehicle for transfers", 
         "Professional Egyptologist tour guide", 
         "Lunch at a local restaurant in Luxor", 
         "Snacks, cold drinks, and water on your way back", 
         "Entrance fees to Karnak Temple (If selected)", 
         "Entrance fees to Valley of the Kings (If selected)", 
         "Visit to the Mortuary Temple of Hatshepsut (If selected)", 
         "Visit to the Colossi of Memnon" 
       ], 
       "whats_not_included": [ 
         "Drinks at the restaurant", 
         "Any personal expenses", 
         "Tips or gratuities (optional)", 
         "Pickup from North Marsa Alam (available with extra charges - €10.00 per person)" 
       ], 
       "meeting_and_pickup": { 
         "pickup_points": "Select a pickup point", 
         "pickup_details": "Please be ready in your hotel lobby at least 10 minutes before the scheduled pickup time. Kindly share your hotel name and room number to ensure a smooth pickup. Pickup available from all hotels and resorts in Marsa Alam", 
         "start_time": "2:30 AM" 
       }, 
       "itinerary": [ 
         { "stop": "Temple of Karnak", "type": "Stop", "description": "Explore the largest temple complex ever built, dedicated to the god Amun-Ra." },
         { "stop": "Temple of Hatshepsut", "type": "Stop", "description": "Admire the stunning terraced temple built for Egypt's most powerful female pharaoh." },
         { "stop": "KV62 - Tomb of Tutankhamun", "type": "Stop", "description": "Step inside the legendary burial place of the boy king (Entrance fee extra)." },
         { "stop": "Colossi of Memnon", "type": "Stop", "description": "Marvel at the two massive stone statues of Pharaoh Amenhotep III." },
         { "stop": "Valley of the Kings", "type": "Stop", "description": "Step into Egypt's legendary burial ground of the pharaohs." } 
       ], 
       "additional_info": [ 
         "Confirmation will be received at time of booking", 
         "Not wheelchair accessible", 
         "Not recommended for travelers with back problems", 
         "No heart problems or other serious medical conditions", 
         "Most travelers can participate", 
         "This tour/activity will have a maximum of 100 travelers" 
       ], 
       "supplier": { 
         "name": "FTS Travels", 
         "rating": "TripAdvisor Reviews: 2 (5.0 Stars)" 
       }, 
       "cancellation_policy": { 
         "description": "You can cancel up to 24 hours in advance of the experience for a full refund.", 
         "free_cancellation": "up to 24 hours before the experience starts (local time)" 
       }, 
       "booking_options": { 
         "reserve_now_pay_later": True, 
         "reserve_now_pay_later_description": "Secure your spot while staying flexible" 
       } 
     },
    "14976P124": { 
       "tour_info": { 
         "platform": "Viator", 
         "url": "https://www.viator.com/tours/Sharm-el-Sheikh/From-Sharm-ElSheikh-The-Lost-City-Petra-Day-Tour-by-Ferry/d827-14976P124", 
         "product_code": "14976P124", 
         "title": "from sharm elsheikh the lost city petra day tour by ferry", 
         "location": "Sharm el Sheikh, Egypt", 
         "category": "Day Trips", 
         "breadcrumb": ["Home", "Things to do in Egypt", "Things to do in Red Sea", "Things to do in Sharm el Sheikh", "Sharm el Sheikh Tours", "Day Trips"] 
       }, 
       "pricing": { 
         "price_from": 255.00, 
         "currency": "USD", 
         "price_unit": "per person", 
         "discounted_rates_for_kids": True, 
         "lowest_price_guarantee": True 
       }, 
       "overview": { 
         "description": "Start with pickup from Sharm El Sheikh and travel through the Sinai Peninsula to Taba. From here, take a ferry across the Gulf of Aqaba to Jordan. Make your way to the gorge of Ma'an, where the ancient city of Petra can be found. A UNESCO World Heritage Site and one of the New Wonders of the World, the city was once described as being \"forgotten by the world for over 1,000 years\". Petra is home to towering buildings carved into the pink stone. On your tour of the canyon, admire the sight of the Treasure Palace, the Roman Theater, and the Temple and Treasures of the Citadel. One of the most astounding archaeological sites in the world, this tour will allow you to check it off your bucket list. After exploring Petra, enjoy lunch in a local restaurant before heading back to Sharm El Sheikh.", 
         "highlights": [ 
           "UNESCO World Heritage Site - Petra", 
           "One of the New Wonders of the World", 
           "Ferry crossing across the Gulf of Aqaba", 
           "Visit the Treasure Palace (Al Khazneh)", 
           "See the Roman Theater", 
           "Explore the Temple and Treasures of the Citadel", 
           "Lunch in local restaurant included", 
           "Ancient city carved into pink stone" 
         ], 
         "duration": "1 day (approx.)", 
         "start_time": "12:30 AM", 
         "languages": ["English"] 
       }, 
       "features": { 
         "pickup_offered": True, 
         "group_discounts": False, 
         "mobile_ticket": True, 
         "wheelchair_accessible": False, 
         "private_tour": False, 
         "small_group": False, 
         "max_travelers": 150 
       }, 
       "whats_included": [ 
         "Hotel pickup and drop-off", 
         "Transportation in air-conditioned vehicle", 
         "Ferry tickets", 
         "Entry visa to Jordan", 
         "Petra entrance fees", 
         "Tour guide on-site", 
         "Lunch" 
       ], 
       "whats_not_included": [ 
         "Tips" 
       ], 
       "meeting_and_pickup": { 
         "pickup_points": "Select a pickup point", 
         "pickup_details": "Your guide Will be waiting infront of the Hotel main Gate holding sign with Company name. Pickup available from Hotels in Sharm El Sheikh", 
         "start_time": "12:30 AM" 
       }, 
       "itinerary": [ 
         { "stop": "Petra", "type": "Stop", "description": "Discover the ancient city of Petra on a day tour from Sharm El Sheikh. Visit the treasury of Al Khazneh, the Roman Theater, and the graves in the King Wall." } 
       ], 
       "additional_info": [ 
         "Confirmation will be received at time of booking", 
         "Not wheelchair accessible", 
         "Stroller accessible", 
         "Infant seats available", 
         "Most travelers can participate", 
         "This tour/activity will have a maximum of 150 travelers" 
       ], 
       "supplier": { 
         "name": "FTS Travels", 
         "rating": "TripAdvisor Reviews: 1236 (Operator)" 
       }, 
       "cancellation_policy": { 
         "description": "You can cancel up to 24 hours in advance of the experience for a full refund.", 
         "free_cancellation": "up to 24 hours before the experience starts (local time)" 
       }, 
       "booking_options": { 
         "reserve_now_pay_later": False, 
         "reserve_now_pay_later_description": "Check availability" 
       } 
     },
    "14976P121": { 
       "tour_info": { 
         "platform": "Viator", 
         "url": "https://www.viator.com/tours/Sharm-el-Sheikh/Sharm-ElSheikh-ATV-Quad-and-Buggy-Adventure-Sunrise-or-Sunset/d827-14976P121", 
         "product_code": "14976P121", 
         "title": "Sharm ElSheikh: ATV Quad & Buggy Adventure Sunrise or Sunset", 
         "location": "Sharm el Sheikh, Egypt", 
         "category": "4WD, ATV & Off-Road Tours", 
         "breadcrumb": ["Home", "Things to do in Egypt", "Things to do in Red Sea", "Things to do in Sharm el Sheikh", "Sharm el Sheikh Tours", "Outdoors", "4WD, ATV & Off-Road Tours"] 
       }, 
       "pricing": { 
         "price_from": 17.00, 
         "currency": "USD", 
         "price_unit": "per person", 
         "discounted_rates_for_kids": True, 
         "lowest_price_guarantee": True 
       }, 
       "overview": { 
         "description": "Start your journey getting picked up from your hotel in Sharm El Sheikh. When you reach the ATV base, you will be given a short introduction and provided with safety guidelines on how to use the quad bike. Begin your quad biking journey, traversing the vast desert landscape. If you opt for a Sunrise Adventure, you will experience the magnificence of the desert as the sun ascends over the horizon. In the case of a Sunset Adventure, you will delight in observing the sky's varying hues as the sun sets.", 
         "highlights": [ 
           "ATV quad biking through Sinai desert", 
           "Choice of Sunrise or Sunset adventure", 
           "Traverse sandy dunes and desert landscape", 
           "Photo opportunities at scenic locations", 
           "Safety introduction and guidelines provided", 
           "Hotel pickup and drop-off included" 
         ], 
         "duration": "3 hours (approx.)", 
         "start_time": "5:00 PM", 
         "languages": ["English", "and 3 more"] 
       }, 
       "features": { 
         "pickup_offered": True, 
         "group_discounts": True, 
         "mobile_ticket": True, 
         "wheelchair_accessible": False, 
         "private_tour": False, 
         "small_group": False, 
         "max_travelers": 50 
       }, 
       "whats_included": [ 
         "Hotel pickup and drop-off in Sharm el Sheikh", 
         "Transfers by air-conditioned vehicle", 
         "Guide", 
         "Mineral water", 
         "Scarf & Goggles" 
       ], 
       "whats_not_included": [ 
         "Tips" 
       ], 
       "meeting_and_pickup": { 
         "pickup_points": "Select a pickup point", 
         "pickup_details": "Pickup available from Hotels in Sharm El Sheikh", 
         "start_time": "5:00 PM" 
       }, 
       "itinerary": [ 
         { "stop": "Sharm El Sheikh Desert", "type": "Stop", "description": "Drive through the sandy dunes of the Sinai desert on a sunrise or sunset ATV quad tour." } 
       ], 
       "additional_info": [ 
         "Confirmation will be received at time of booking", 
         "Not wheelchair accessible", 
         "Infant seats available", 
         "Not recommended for pregnant travelers", 
         "Most travelers can participate", 
         "This tour/activity will have a maximum of 50 travelers" 
       ], 
       "supplier": { 
         "name": "FTS Travels", 
         "rating": "TripAdvisor Reviews: 4 (5.0 Stars)" 
       }, 
       "cancellation_policy": { 
         "description": "You can cancel up to 24 hours in advance of the experience for a full refund.", 
         "free_cancellation": "up to 24 hours before the experience starts (local time)" 
       }, 
       "booking_options": { 
         "reserve_now_pay_later": True, 
         "reserve_now_pay_later_description": "Secure your spot while staying flexible" 
       } 
     },
    "14976P120": { 
       "tour_info": { 
         "platform": "Viator", 
         "url": "https://www.viator.com/tours/Sharm-el-Sheikh/Sharm-El-Sheikh-Ras-Mohamed-Half-Day-Tour-and-Allahs-Gate/d827-14976P120", 
         "product_code": "14976P120", 
         "title": "Sharm El-Sheikh: Ras Mohamed Half-Day Tour and Allah's Gate", 
         "location": "Sharm el Sheikh, Egypt", 
         "category": "Half-day Tours", 
         "breadcrumb": ["Home", "Things to do in Egypt", "Things to do in Red Sea", "Things to do in Sharm el Sheikh", "Sharm el Sheikh Tours", "Outdoors", "Half-day Tours"] 
       }, 
       "pricing": { 
         "price_from": 12.00, 
         "currency": "USD", 
         "price_unit": "per person", 
         "discounted_rates_for_kids": True, 
         "lowest_price_guarantee": True 
       }, 
       "overview": { 
         "description": "Be collected at your accommodation in Sharm by a modern air-conditioned mini-bus. Take a short drive to the Ras Mohammed National Park. Your guide will tell you about what you're likely to see on the way there. Have the opportunity to go snorkeling in Egypt's most beautiful reef. Marvel at a remarkably colorful underwater world. Mangroves are the only trees that grow in saltwater. In the Ras Mohammed National Park, you can find these unique trees that are actually native to Central Africa. Discover the Magic Lake, a large deep lake suitable for swimming. The Bedouin gave his name to the magic lake and you will learn fantastic stories about him. After your snorkeling experience at the Ras Mohammed National Park, be returned to your accommodation.", 
         "highlights": [ 
           "Visit Ras Mohammed National Park", 
           "Snorkeling in Egypt's most beautiful reef", 
           "See unique mangroves (trees that grow in saltwater)", 
           "Visit Allah's Gate", 
           "Discover the Magic Lake (swimming opportunity)", 
           "Air-conditioned mini-bus transport" 
         ], 
         "duration": "5 hours (approx.)", 
         "start_time": "9:00 AM", 
         "languages": ["English", "and 3 more"] 
       }, 
       "features": { 
         "pickup_offered": True, 
         "group_discounts": False, 
         "mobile_ticket": True, 
         "wheelchair_accessible": False, 
         "private_tour": False, 
         "small_group": False, 
         "max_travelers": 500 
       }, 
       "whats_included": [ 
         "Hotel pickup and drop-off in an air-conditioned vehicle", 
         "Certified snorkeling guide", 
         "Allah's Gate visit" 
       ], 
       "whats_not_included": [ 
         "Use of snorkeling equipment (available to rent from shop)", 
         "Ras Mohammed National Park entrance fee (€10.00 per person)" 
       ], 
       "meeting_and_pickup": { 
         "pickup_points": "Select a pickup point", 
         "pickup_details": "Pickup available from Hotels in Sharm El-Sheikh", 
         "start_time": "9:00 AM" 
       }, 
       "itinerary": [ 
         { "stop": "Ras Mohammed National Park", "type": "Stop", "description": "Enjoy a fantastic day trip from Sharm El-Sheikh to Ras Mohammed." } 
       ], 
       "additional_info": [ 
         "Confirmation will be received at time of booking", 
         "Not wheelchair accessible", 
         "Infants must sit on laps", 
         "Infant seats available", 
         "Most travelers can participate", 
         "This tour/activity will have a maximum of 500 travelers" 
       ], 
       "supplier": { 
         "name": "FTS Travels", 
         "rating": "TripAdvisor Reviews: 32 (5.0 Stars)" 
       }, 
       "cancellation_policy": { 
         "description": "You can cancel up to 24 hours in advance of the experience for a full refund.", 
         "free_cancellation": "up to 24 hours before the experience starts (local time)" 
       }, 
       "booking_options": { 
         "reserve_now_pay_later": True, 
         "reserve_now_pay_later_description": "Secure your spot while staying flexible" 
       } 
     },
    "14976P119": { 
       "tour_info": { 
         "platform": "Viator", 
         "url": "https://www.viator.com/tours/Sharm-el-Sheikh/Sharm-El-Sheikh-Mount-Sinai-and-St-Catherine-Monastery-Tour/d827-14976P119", 
         "product_code": "14976P119", 
         "title": "Sharm El Sheikh Mount Sinai and St. Catherine Monastery Tour", 
         "location": "Sharm el Sheikh, Egypt", 
         "category": "Overnight Tours", 
         "breadcrumb": ["Home", "Things to do in Egypt", "Things to do in Red Sea", "Things to do in Sharm el Sheikh", "Sharm el Sheikh Tours", "Tours & Sightseeing", "Overnight Tours"] 
       }, 
       "pricing": { 
         "price_from": 30.00, 
         "currency": "USD", 
         "price_unit": "per person", 
         "discounted_rates_for_kids": True, 
         "lowest_price_guarantee": True 
       }, 
       "overview": { 
         "description": "A representative will greet you at your hotel in Sharm El Sheikh You'll be whisked away in a modern, air-conditioned Bus to St. Catherine, a drive of approximately three hours. Your adventure begins with an ascent of Moses Mountain before dawn, As you climb, feel the tranquility of the night and the anticipation of the breathtaking view that awaits. Take in panoramic views over the Sinai desert before you begin your climb down to the monastery. Your journey continues with a visit to the renowned St. Catherine Monastery, one of the world's most famous monasteries The monastery was established in AD 565. This sacred site was dedicated to Saint Catherine, one of Alexander's rulers who embraced her faith so profoundly that she endured torture and death for it. At the end of your tour, you'll be transferred back to your accommodation in Sharm El Sheikh.", 
         "highlights": [ 
           "Climb Mount Sinai overnight", 
           "Watch spectacular sunrise from mountain top", 
           "Panoramic views over Sinai desert", 
           "Visit St. Catherine Monastery (established AD 565)", 
           "One of the world's most famous monasteries", 
           "Sacred site dedicated to Saint Catherine", 
           "Air-conditioned bus transportation", 
           "3-hour drive to St. Catherine" 
         ], 
         "duration": "12 hours (approx.)", 
         "start_time": "8:30 PM", 
         "languages": ["English", "and 1 more"] 
       }, 
       "features": { 
         "pickup_offered": True, 
         "group_discounts": True, 
         "mobile_ticket": True, 
         "wheelchair_accessible": False, 
         "private_tour": False, 
         "small_group": False, 
         "max_travelers": 500 
       }, 
       "whats_included": [ 
         "Hotel pickup and drop-off", 
         "Transportation by air-conditioned bus", 
         "Tour guide" 
       ], 
       "whats_not_included": [ 
         "Tips", 
         "Camel ride (€10.00 per person)", 
         "Government Fees (€10.00 per person)" 
       ], 
       "meeting_and_pickup": { 
         "pickup_points": "Select a pickup point", 
         "pickup_details": "Sharm El Sheikh hotels and private accommodations. Please be ready in your hotel lobby 10–15 minutes before the scheduled pickup time.", 
         "start_time": "8:30 PM" 
       }, 
       "itinerary": [ 
         { "stop": "Mount Sinai", "type": "Stop", "description": "Climb to the top of Mount Sinai overnight, Enjoy the spectacular sunrise. then descend to St. Catherine's Monastery with a guide." } 
       ], 
       "additional_info": [ 
         "Confirmation will be received at time of booking", 
         "Not wheelchair accessible", 
         "Not recommended for travelers with back problems", 
         "No heart problems or other serious medical conditions", 
         "Travelers should have a moderate physical fitness level", 
         "This tour/activity will have a maximum of 500 travelers" 
       ], 
       "supplier": { 
         "name": "FTS Travels", 
         "rating": "TripAdvisor Reviews: 3 (4.5 Stars)" 
       }, 
       "cancellation_policy": { 
         "description": "You can cancel up to 24 hours in advance of the experience for a full refund.", 
         "free_cancellation": "up to 24 hours before the experience starts (local time)" 
       }, 
       "booking_options": { 
         "reserve_now_pay_later": True, 
         "reserve_now_pay_later_description": "Secure your spot while staying flexible" 
       } 
     },
     "14976P118": { 
       "tour_info": { 
         "platform": "Viator", 
         "url": "https://www.viator.com/tours/Sharm-el-Sheikh/Sharm-El-Sheikh-City-Tour-with-Optional-Seafood-Meal/d827-14976P118", 
         "product_code": "14976P118", 
         "title": "Sharm El-Sheikh City Tour with Optional Seafood Meal", 
         "location": "Sharm el Sheikh, Egypt", 
         "category": "City Tours", 
         "breadcrumb": ["Home", "Things to do in Egypt", "Things to do in Red Sea", "Things to do in Sharm el Sheikh", "Sharm el Sheikh Tours", "Tours & Sightseeing", "City Tours"] 
       }, 
       "pricing": { 
         "price_from": 10.77, 
         "currency": "USD", 
         "price_unit": "per person", 
         "discounted_rates_for_kids": True, 
         "lowest_price_guarantee": True 
       }, 
       "overview": { 
         "description": "Experience the perfect blend of culture, shopping, and leisure on this enriching city tour. Begin with a visit to the magnificent Al Mustafa Mosque, a masterpiece of Islamic architecture, followed by the iconic El Sahaba Mosque, an Old Market landmark admired for its striking design. After exploring these cultural gems, enjoy free time at the vibrant Old Market, where colorful stalls invite you to browse for souvenirs, aromatic spices, traditional crafts, and unique local treasures. For those wishing to add a flavorful touch, you'll have the option to savor a fresh seafood feast at Fares Restaurant, one of Sharm's most celebrated dining spots, renowned for its authentic recipes and daily catch. Whether you're drawn to cultural sights, lively shopping, or a memorable dining experience, this tour combines the very best of Sharm El-Sheikh into one unforgettable journey.", 
         "highlights": [ 
           "Visit Al Mustafa Mosque - Islamic architecture masterpiece", 
           "See El Sahaba Mosque - Old Market landmark", 
           "Free time at vibrant Old Market", 
           "Shop for souvenirs, spices, and crafts", 
           "Optional seafood meal at Fares Restaurant", 
           "Visit Naama Bay promenade", 
           "Peace Memorial and Al Fanar Lighthouse", 
           "Soho Square - entertainment hub" 
         ], 
         "duration": "3 hours (approx.)", 
         "start_time": "Varies", 
         "languages": ["English", "and 2 more"] 
       }, 
       "features": { 
         "pickup_offered": True, 
         "group_discounts": True, 
         "mobile_ticket": True, 
         "wheelchair_accessible": False, 
         "private_tour": False, 
         "small_group": False, 
         "max_travelers": 500 
       }, 
       "whats_included": [ 
         "Hotel pickup and drop-off", 
         "Transportation in a air-conditioned car", 
         "Local guide" 
       ], 
       "whats_not_included": [], 
       "meeting_and_pickup": { 
         "pickup_points": "Select a pickup point", 
         "pickup_details": "You will find the guide waiting for you and holding a sign with the company logo. Pickup available from Hotels in Sharm El-Sheikh", 
         "start_time": "Varies" 
       }, 
       "itinerary": [ 
         { "stop": "Old Market", "type": "Stop", "description": "Discover the charm of Sharm El Sheikh on a guided city tour that blends culture, shopping, and stunning views." } 
       ], 
       "additional_info": [ 
         "Confirmation will be received at time of booking", 
         "Not wheelchair accessible", 
         "Stroller accessible", 
         "Infant seats available", 
         "Most travelers can participate", 
         "This tour/activity will have a maximum of 500 travelers" 
       ], 
       "supplier": { 
         "name": "FTS Travels", 
         "rating": "TripAdvisor Reviews: 9 (5.0 Stars)" 
       }, 
       "cancellation_policy": { 
         "description": "You can cancel up to 24 hours in advance of the experience for a full refund.", 
         "free_cancellation": "up to 24 hours before the experience starts (local time)" 
       }, 
       "booking_options": { 
         "reserve_now_pay_later": True, 
         "reserve_now_pay_later_description": "Secure your spot while staying flexible" 
       } 
     },
    "14976P115": { 
       "tour_info": { 
         "platform": "Viator", 
         "url": "https://www.viator.com/tours/Giza/Cairo-Grand-Egyptian-Museum-QR-Ticket/d23032-14976P115", 
         "product_code": "14976P115", 
         "title": "Grand Egyptian Museum QR Ticket in Cairo", 
         "location": "Giza, Egypt", 
         "category": "Museum Tickets & Passes", 
         "breadcrumb": ["Home", "Things to do in Egypt", "Things to do in Giza", "Giza Tours", "Attractions & Museums", "Museum Tickets & Passes"] 
       }, 
       "pricing": { 
         "price_from": 20.78, 
         "currency": "USD", 
         "price_unit": "per person", 
         "discounted_rates_for_kids": True, 
         "lowest_price_guarantee": True 
       }, 
       "overview": { 
         "description": "Skip the hassle with a QR ticket that grants you direct access to the world's largest archaeological museum dedicated to a single civilization. Explore at your own pace the legendary Tutankhamun treasures displayed together for the first time. Admire colossal statues on the Grand Staircase. Immerse yourself in the rich history of ancient Egypt in one of the most anticipated cultural landmarks in the world.", 
         "highlights": [ 
           "Skip the hassle with a QR ticket", 
           "Direct access to the world's largest archaeological museum", 
           "Explore at your own pace", 
           "See Tutankhamun treasures", 
           "Admire colossal statues on the Grand Staircase" 
         ], 
         "duration": "2 to 3 hours (approx.)", 
         "start_time": "Varies", 
         "languages": ["English"] 
       }, 
       "features": { 
         "pickup_offered": False, 
         "group_discounts": True, 
         "mobile_ticket": True, 
         "wheelchair_accessible": False, 
         "private_tour": False, 
         "small_group": False, 
         "max_travelers": 999 
       }, 
       "whats_included": [ 
         "Entry ticket to the Grand Egyptian Museum", 
         "Transfer ( UPON REQUEST )" 
       ], 
       "whats_not_included": [], 
       "meeting_and_pickup": { 
         "pickup_points": "Grand Egyptian Muesum, Cairo - Alexandria Dessert Road, Giza 3513204 Egypt", 
         "pickup_details": "Meeting point at the museum entrance.", 
         "start_time": "Varies" 
       }, 
       "itinerary": [ 
         { "stop": "Grand Egyptian Museum", "type": "Stop", "description": "Explore the museum galleries, Grand Staircase, and Atrium at your own pace." } 
       ], 
       "additional_info": [ 
         "Confirmation will be received at time of booking", 
         "Not wheelchair accessible", 
         "Most travelers can participate" 
       ], 
       "supplier": { 
         "name": "FTS Travels", 
         "rating": "TripAdvisor Reviews: 69 (5.0 Stars)" 
       }, 
       "cancellation_policy": { 
         "description": "You can cancel up to 24 hours in advance of the experience for a full refund.", 
         "free_cancellation": "up to 24 hours before the experience starts (local time)" 
       }, 
       "booking_options": { 
         "reserve_now_pay_later": True, 
         "reserve_now_pay_later_description": "Secure your spot while staying flexible" 
       } 
     },
    "14976P114": { 
       "tour_info": { 
         "platform": "Viator", 
         "url": "https://www.viator.com/tours/Sharm-el-Sheikh/Sharm-El-Sheikh-Full-Day-Tour-of-Cairo-and-Pyramids-by-Bus/d827-14976P114", 
         "product_code": "14976P114", 
         "title": "Discover Cairo & the Great Pyramids – Full Day From Sharm By Bus", 
         "location": "Sharm el Sheikh, Egypt", 
         "category": "Day Trips", 
         "breadcrumb": ["Home", "Things to do in Egypt", "Things to do in Red Sea", "Things to do in Sharm el Sheikh", "Sharm el Sheikh Tours", "Day Trips"] 
       }, 
       "pricing": { 
         "price_from": 90.00, 
         "currency": "USD", 
         "price_unit": "per person", 
         "discounted_rates_for_kids": True, 
         "lowest_price_guarantee": True 
       }, 
       "overview": { 
         "description": "Comfortable round-trip transport by air-conditioned bus with hotel pickup and drop-off included. An expert Egyptologist guide who brings ancient history to life with engaging stories and insights. Comprehensive itinerary covering the Pyramids of Giza, the Great Sphinx, the Egyptian Museum, and the vibrant Khan El Khalili Bazaar (If we have time) – all in a single day. An optional Nile River boat ride adds a unique perspective of Cairo.", 
         "highlights": [ 
           "Comfortable round-trip transport by air-conditioned bus", 
           "Expert Egyptologist guide", 
           "Visit Pyramids of Giza and Great Sphinx", 
           "Explore the Egyptian Museum", 
           "Optional Nile River boat ride" 
         ], 
         "duration": "1 day (approx.)", 
         "start_time": "12:30 am", 
         "languages": ["English", "and 4 more"] 
       }, 
       "features": { 
         "pickup_offered": True, 
         "group_discounts": True, 
         "mobile_ticket": True, 
         "wheelchair_accessible": False, 
         "private_tour": False, 
         "small_group": True, 
         "max_travelers": 12 
       }, 
       "whats_included": [ 
         "Hotel pickup and drop-off", 
         "Transportation by air-conditioned bus", 
         "Tour guide" 
       ], 
       "whats_not_included": [ 
         "Visa, if required (35$ to be paid in cash onsite)" 
       ], 
       "meeting_and_pickup": { 
         "pickup_points": "Select a pickup point", 
         "pickup_details": "Pickup is available from all hotels in Sharm El-Sheikh. Pickup usually starts about 1 hour before departure.", 
         "start_time": "12:30 am" 
       }, 
       "itinerary": [ 
         { "stop": "Pyramids of Giza", "type": "Stop", "description": "Marvel at the last remaining wonder of the ancient world and learn the history of Egypt's most iconic monuments." },
         { "stop": "Great Sphinx", "type": "Stop", "description": "Admire the legendary limestone statue with the body of a lion and the head of a Pharaoh." },
         { "stop": "The Egyptian Museum in Cairo", "type": "Stop", "description": "Explore thousands of artifacts, including treasures from Tutankhamun's tomb." },
         { "stop": "Nile River", "type": "Stop", "description": "(Optional felucca boat ride) – Enjoy views of Cairo from the water." } 
       ], 
       "additional_info": [ 
         "Confirmation will be received at time of booking", 
         "Not wheelchair accessible", 
         "Not recommended for travelers with back problems", 
         "No heart problems or other serious medical conditions", 
         "Most travelers can participate", 
         "This tour/activity will have a maximum of 12 travelers" 
       ], 
       "supplier": { 
         "name": "FTS Travels", 
         "rating": "TripAdvisor Reviews: 27 (5.0 Stars)" 
       }, 
       "cancellation_policy": { 
         "description": "You can cancel up to 24 hours in advance of the experience for a full refund.", 
         "free_cancellation": "up to 24 hours before the experience starts (local time)" 
       }, 
       "booking_options": { 
         "reserve_now_pay_later": True, 
         "reserve_now_pay_later_description": "Secure your spot while staying flexible" 
       } 
     },
    "14976P113": { 
       "tour_info": { 
         "platform": "Viator", 
         "url": "https://www.viator.com/tours/Cairo/Egyptian-Civilization-Museum-Citadel-and-Old-Cairo-Tour/d782-14976P113", 
         "product_code": "14976P113", 
         "title": "QR Ticket -Egyptian Civilization Museum, Citadel & Old Cairo Tour", 
         "location": "Cairo, Egypt", 
         "category": "Day Trips", 
         "breadcrumb": ["Home", "Things to do in Egypt", "Things to do in Cairo", "Cairo Tours", "Day Trips"] 
       }, 
       "pricing": { 
         "price_from": 40.00, 
         "currency": "USD", 
         "price_unit": "per person", 
         "discounted_rates_for_kids": True, 
         "lowest_price_guarantee": True 
       }, 
       "overview": { 
         "description": "Discover Egypt's rich history on a fascinating full-day cultural tour through Cairo's most iconic landmarks. Begin your journey at the National Museum of Egyptian Civilization, home to the famous Royal Mummies Hall. Continue to the impressive Citadel of Salah El-Din and visit the stunning Mohamed Ali Mosque. End your experience in Old Cairo, where you'll walk through historic streets and visit significant religious sites. This tour is perfect for travelers who want to experience Egypt's civilization, religion, and architecture all in one enriching day, guided by a knowledgeable Egyptologist.", 
         "highlights": [ 
           "Visit National Museum of Egyptian Civilization (Royal Mummies Hall)", 
           "Explore Citadel of Salah El-Din and Mohamed Ali Mosque", 
           "Walk through Old Cairo (Coptic Cairo)", 
           "Visit Hanging Church, Abu Serga Church, and Ben Ezra Synagogue", 
           "Full-day cultural tour with Egyptologist guide" 
         ], 
         "duration": "8 hours (approx.)", 
         "start_time": "08:00 AM", 
         "languages": ["English", "and 4 more"] 
       }, 
       "features": { 
         "pickup_offered": True, 
         "group_discounts": True, 
         "mobile_ticket": True, 
         "wheelchair_accessible": False, 
         "private_tour": True, 
         "small_group": False, 
         "max_travelers": 50 
       }, 
       "whats_included": [ 
         "Hotel pickup and drop-off (Cairo or Giza)", 
         "Transportation in an air-conditioned vehicle", 
         "Licensed professional Egyptologist guide",
         "Entrance fees (if option selected)" 
       ], 
       "whats_not_included": [ 
         "Drinks", 
         "Personal expenses", 
         "Optional activities not mentioned in the itinerary" 
       ], 
       "meeting_and_pickup": { 
         "pickup_points": "Select a pickup point", 
         "pickup_details": "Pickup is available from Cairo hotels, private accommodations, or central meeting points. Please be ready in the hotel lobby 10–15 minutes before the scheduled pickup time.", 
         "start_time": "08:00 AM" 
       }, 
       "itinerary": [ 
         { "stop": "National Museum of Egyptian Civilization", "type": "Stop", "description": "Explore the museum highlights, including the Royal Mummies Hall." },
         { "stop": "Citadel of Salah El-Din", "type": "Stop", "description": "Visit the historic Cairo Citadel and Mohamed Ali Mosque." },
         { "stop": "Old Cairo", "type": "Stop", "description": "Walk through Coptic Cairo, visiting ancient churches and synagogues." } 
       ], 
       "additional_info": [ 
         "Confirmation will be received at time of booking", 
         "Not wheelchair accessible", 
         "Stroller accessible", 
         "Most travelers can participate", 
         "This is a private tour/activity. Only your group will participate" 
       ], 
       "supplier": { 
         "name": "FTS Travels", 
         "rating": "TripAdvisor Reviews: 176 (Operator)" 
       }, 
       "cancellation_policy": { 
         "description": "You can cancel up to 24 hours in advance of the experience for a full refund.", 
         "free_cancellation": "up to 24 hours before the experience starts (local time)" 
       }, 
       "booking_options": { 
         "reserve_now_pay_later": True, 
         "reserve_now_pay_later_description": "Secure your spot while staying flexible" 
       } 
     }
}

def update_data():
    try:
        if not os.path.exists(FILE_PATH):
            print("File not found!")
            return

        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        updated_count = 0
        added_count = 0
        
        # Create a map of existing products for quick lookup
        existing_products = {trip.get('tour_info', {}).get('product_code'): i for i, trip in enumerate(data)}
        
        for code, new_trip_data in NEW_DATA_MAP.items():
            if code in existing_products:
                print(f"Updating trip: {code}")
                index = existing_products[code]
                data[index] = new_trip_data
                updated_count += 1
            else:
                print(f"Adding new trip: {code}")
                data.append(new_trip_data)
                added_count += 1
                
        # Save back
        with open(FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Operations completed: {updated_count} updated, {added_count} added. Total in file: {len(data)}")
        
    except Exception as e:
        print(f"❌ Error updating data: {e}")

if __name__ == "__main__":
    update_data()
