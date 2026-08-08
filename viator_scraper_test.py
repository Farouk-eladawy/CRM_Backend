import json
import time
import random
import os
import re
import traceback
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

INPUT_FILE = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\Viator links_test.txt"
OUTPUT_FILE = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\Viator_data_test.json"

# --- SELECTORS PROVIDED BY USER ---
VIATOR_XPATH = {
    "title": "//h1",
    "location": "//span[contains(text(), ', Egypt')] | //div[contains(@class, 'location')]",
    "product_code": "//text()[contains(., 'Product code:')]/following-sibling::text()[1]",
    
    "price_value": "//span[contains(text(), '$')] | //div[@data-test-id='price-from']//span | //div[contains(@class, 'price')]//span",
    
    "duration": "//*[contains(text(), 'hours') and (contains(text(), '8') or contains(text(), 'approx'))]",
    
    "overview_description": "//section[@aria-labelledby='overview']//p | //div[contains(@class, 'overview')]//p | //div[@id='overview']//div[contains(@class, 'content')]",
    
    "whats_included_list": "//div[.//h2[contains(text(), \"What's Included\")]]//li[.//svg[contains(@class, 'check')]]",
    "whats_not_included_list": "//div[.//h2[contains(text(), \"What's Included\")]]//li[.//svg[contains(@class, 'x')]]",
    
    "itinerary_stops": "//div[.//h2[contains(text(), 'Itinerary')]]//div[contains(@class, 'stop')] | //div[contains(@class, 'timeline-item')]",
    "itinerary_stop_names": ".//h3 | .//strong | .//span[contains(@class, 'title')]",
    "itinerary_stop_descriptions": ".//p[not(contains(@class, 'type'))] | .//div[contains(@class, 'description')]",
    
    "additional_info_items": "//div[.//h2[contains(text(), 'Additional Info')]]//li",
    
    "supplier_name": "//button[contains(text(), 'Supplied by')] | //span[contains(text(), 'Supplied by')]/following-sibling::button",
    
    "cancellation_text": "//div[.//h2[contains(text(), 'Cancellation')]]//p",
    
    "free_cancellation": "//*[contains(text(), 'Free cancellation')] | //*[contains(text(), 'cancel up to 24 hours')]"
}

def clean_text(text):
    if text:
        return " ".join(text.strip().replace('\u2013', '-').replace('\u2019', "'").split())
    return ""

def extract_code_from_url(url):
    match = re.search(r'(\d+P\d+)', url)
    return match.group(1) if match else "UNKNOWN"

def create_skeleton_object(url):
    # Fallback skeleton
    code = extract_code_from_url(url)
    try:
        slug = url.split('/')[5]
        title = slug.replace('-', ' ')
    except:
        title = "Viator Tour"
        
    return {
        "tour_info": {
            "platform": "Viator",
            "url": url,
            "product_code": code,
            "title": title,
            "location": "Egypt",
            "category": "Tours",
            "breadcrumb": ["Home", "Egypt"]
        },
        "pricing": {
            "price_from": 50.00,
            "currency": "USD",
            "price_unit": "per person",
            "discounted_rates_for_kids": True,
            "lowest_price_guarantee": True
        },
        "overview": {
            "description": f"Enjoy the {title}. Provided by FTS Travels.",
            "duration": "Flexible",
            "start_time": "Varies",
            "languages": ["English"]
        },
        "features": {
            "pickup_offered": True,
            "mobile_ticket": True,
            "wheelchair_accessible": False,
            "private_tour": "Private" in title
        },
        "whats_included": ["Hotel pickup and drop-off", "Transport"],
        "whats_not_included": ["Gratuities"],
        "meeting_and_pickup": {
            "pickup_points": "Hotel Lobby",
            "pickup_details": "Please be ready 15 mins before.",
            "start_time": "08:00 AM"
        },
        "itinerary": [],
        "additional_info": ["Confirmation received at booking"],
        "supplier": {"name": "FTS Travels"},
        "cancellation_policy": {
            "description": "Free cancellation up to 24 hours in advance.",
            "free_cancellation": "24 hours"
        },
        "booking_options": {
            "reserve_now_pay_later": True,
            "reserve_now_pay_later_description": "Secure your spot"
        }
    }

def scrape_trips():
    # Read URLs
    urls = []
    if os.path.exists(INPUT_FILE):
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                parts = line.strip().split('http')
                if len(parts) > 1:
                    urls.append('http' + parts[1].strip())
                elif line.strip().startswith('http'):
                    urls.append(line.strip())
    
    print(f"Found {len(urls)} links to process.")
    all_tours = []

    try:
        with sync_playwright() as p:
            print("Launching browser...")
            # Launch Browser (Chromium) with Stealth Args
            args = [
                '--disable-blink-features=AutomationControlled',
                '--start-maximized',
                '--disable-infobars',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                '--window-size=1920,1080',
            ]
            
            browser = p.chromium.launch(
                headless=False,
                args=args
            )
            print("Browser launched.")
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='Africa/Cairo',
                permissions=['geolocation']
            )
            
            # Apply Stealth to Context? No, usually per page.
            
            for i, url in enumerate(urls):
                print(f"[{i+1}/{len(urls)}] Scraping: {url}")
                page = context.new_page()
                
                # APPLY STEALTH
                Stealth().apply_stealth_sync(page)
                
                try:
                    # Add random delay before navigation
                    time.sleep(1)
                    
                    response = page.goto(url, timeout=60000, wait_until="domcontentloaded")
                    
                    # --- MANUAL INTERVENTION HANDLER ---
                    # Wait for user to solve CAPTCHA/Blocking
                    print("Checking for access blocks...")
                    max_wait_time = 300  # 5 minutes
                    start_wait = time.time()
                    
                    while time.time() - start_wait < max_wait_time:
                        page_title = page.title().lower()
                        page_content = page.content().lower()
                        
                        is_blocked = (
                            "access blocked" in page_title or 
                            "verification required" in page_title or 
                            "just a moment" in page_title or
                            "challenge" in page_title or
                            "access blocked" in page_content or
                            "verification required" in page_content
                        )
                        
                        # Check if the main content (H1) is visible, meaning we are safe
                        is_content_visible = False
                        try:
                            if page.locator(VIATOR_XPATH["title"]).count() > 0:
                                is_content_visible = True
                        except: pass
                        
                        if is_content_visible:
                            print("✅ Page loaded successfully.")
                            break
                        
                        if is_blocked:
                            print(f"⚠️ BLOCK DETECTED! Please solve the CAPTCHA/Slider in the browser manually. Waiting... ({int(max_wait_time - (time.time() - start_wait))}s left)")
                            time.sleep(5)
                        else:
                            # Might be loading or some other state
                            print("Waiting for page content...")
                            time.sleep(2)
                            
                    # -----------------------------------
                    
                    # Wait a bit for dynamic content
                    time.sleep(2)
                    
                    # --- EXTRACTION ---
                    
                    # 1. Title
                    try:
                        title = clean_text(page.locator(VIATOR_XPATH["title"]).first.inner_text())
                    except: 
                        title = "Unknown Title"

                    # 2. Product Code
                    try:
                        # Try text matching first
                        code = page.locator("xpath=//body").inner_text()
                        match = re.search(r'Product code:\s*(\d+P\d+)', code)
                        if match:
                            product_code = match.group(1)
                        else:
                            # Fallback to URL
                            product_code = extract_code_from_url(url)
                    except:
                        product_code = extract_code_from_url(url)

                    # 3. Price
                    try:
                        price_text = page.locator(VIATOR_XPATH["price_value"]).first.inner_text()
                        price_from = float(re.sub(r'[^\d.]', '', price_text))
                    except:
                        price_from = 0.0
                    
                    currency = "USD"
                    
                    # 4. Overview
                    try:
                        desc_locator = page.locator(VIATOR_XPATH["overview_description"]).first
                        description = clean_text(desc_locator.inner_text())
                    except:
                        description = ""
                    
                    if not description:
                        description = f"Experience {title}."

                    # 5. Features
                    features = {
                        "pickup_offered": page.get_by_text("Pickup offered", exact=False).count() > 0,
                        "mobile_ticket": page.get_by_text("Mobile ticket", exact=False).count() > 0,
                        "wheelchair_accessible": page.get_by_text("Wheelchair accessible", exact=False).count() > 0,
                        "private_tour": "Private" in title
                    }
                    
                    # 6. Inclusions
                    inclusions = []
                    try:
                        incs = page.locator(VIATOR_XPATH["whats_included_list"]).all()
                        inclusions = [clean_text(inc.inner_text()) for inc in incs]
                    except: pass
                    
                    # 7. Exclusions
                    exclusions = []
                    try:
                        excs = page.locator(VIATOR_XPATH["whats_not_included_list"]).all()
                        exclusions = [clean_text(exc.inner_text()) for exc in excs]
                    except: pass

                    # 8. Itinerary
                    itinerary = []
                    try:
                        stops = page.locator(VIATOR_XPATH["itinerary_stops"]).all()
                        for stop in stops:
                            try:
                                s_name = clean_text(stop.locator(VIATOR_XPATH["itinerary_stop_names"]).first.inner_text())
                                s_desc = clean_text(stop.locator(VIATOR_XPATH["itinerary_stop_descriptions"]).first.inner_text())
                                itinerary.append({
                                    "stop": s_name,
                                    "type": "Stop",
                                    "description": s_desc
                                })
                            except: continue
                    except: pass

                    # 9. Additional Info
                    add_info = []
                    try:
                        infos = page.locator(VIATOR_XPATH["additional_info_items"]).all()
                        add_info = [clean_text(info.inner_text()) for info in infos]
                    except: pass

                    # Construct Data
                    tour_data = {
                        "tour_info": {
                            "platform": "Viator",
                            "url": url,
                            "product_code": product_code,
                            "title": title,
                            "location": "Egypt",
                            "category": "Tours",
                            "breadcrumb": ["Home", "Egypt", "Tours"]
                        },
                        "pricing": {
                            "price_from": price_from,
                            "currency": currency,
                            "price_unit": "per person",
                            "discounted_rates_for_kids": True,
                            "lowest_price_guarantee": True
                        },
                        "overview": {
                            "description": description[:1000],
                            "duration": "Flexible",
                            "start_time": "Varies",
                            "languages": ["English"]
                        },
                        "features": features,
                        "whats_included": inclusions if inclusions else ["See website"],
                        "whats_not_included": exclusions,
                        "meeting_and_pickup": {
                            "pickup_points": "Select a pickup point",
                            "pickup_details": "Check voucher for details.",
                            "start_time": "Varies"
                        },
                        "itinerary": itinerary,
                        "additional_info": add_info,
                        "supplier": {
                            "name": "FTS Travels"
                        },
                        "cancellation_policy": {
                            "description": "Check website for policy.",
                            "free_cancellation": "24 hours" if features.get('free_cancellation') else "Check details"
                        },
                        "booking_options": {
                            "reserve_now_pay_later": True,
                            "reserve_now_pay_later_description": "Secure your spot while staying flexible"
                        }
                    }

                    all_tours.append(tour_data)
                    
                    status = "SUCCESS" if tour_data['tour_info']['title'] != "Unknown Title" else "PARTIAL"
                    print(f"✅ Scraped: {tour_data['tour_info']['title']} [{status}]")

                except Exception as e:
                    print(f"❌ Failed {url}: {e}")
                    try:
                        page.screenshot(path=f"error_screenshot_{i}.png")
                        print(f"📸 Screenshot saved to error_screenshot_{i}.png")
                    except:
                        print("Could not take screenshot (browser might be closed)")
                    all_tours.append(create_skeleton_object(url))
                
                # Save periodically
                if (i + 1) % 5 == 0:
                    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                        json.dump(all_tours, f, ensure_ascii=False, indent=2)
                
                # Delay to respect rate limits
                time.sleep(1)
                
                page.close()

            browser.close()
            
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        traceback.print_exc()

    # Final Save
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_tours, f, ensure_ascii=False, indent=2)
    print(f"Done! Saved {len(all_tours)} tours to {OUTPUT_FILE}")

if __name__ == "__main__":
    scrape_trips()
