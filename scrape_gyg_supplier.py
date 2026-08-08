import time
import json
import random
import os
import re
import pyotp
from playwright.sync_api import sync_playwright

INPUT_FILE = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\Get_Your_Guide_trips.txt"
OUTPUT_FILE = "Get_Your_Guide_data.json"

def read_urls(file_path):
    urls = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    url = parts[-1]
                    if url.startswith('http'):
                        urls.append(url)
                elif line.strip().startswith('http'):
                    urls.append(line.strip())
    except Exception as e:
        print(f"Error reading file: {e}")
    return urls

def scrape_trips():
    urls = read_urls(INPUT_FILE)
    print(f"Found {len(urls)} trips to scrape.")
    
    data = []
    
    with sync_playwright() as p:
        user_data_dir = os.path.join(os.getcwd(), "gyg_browser_data")
        print(f"Launching Firefox with persistent context in: {user_data_dir}")
        
        # Use persistent context to save login state
        context = p.firefox.launch_persistent_context(
            user_data_dir,
            headless=False,
            viewport={'width': 1280, 'height': 720}
        )
        page = context.pages[0] if context.pages else context.new_page()
        
        print("Navigating to Supplier Login page...")
        page.goto("https://supplier.getyourguide.com/login")
        
        # --- AUTO LOGIN LOGIC ---
        try:
            print("Attempting Auto-Login...")
            # Wait for email field
            page.wait_for_selector("input[type='email']", timeout=5000)
            
            # Check if we are already logged in (redirected)
            if "login" not in page.url:
                print("Already logged in!")
            else:
                print("Entering credentials...")
                page.fill("input[type='email']", "reisen@aegypten-ausfluege.de")
                page.fill("input[type='password']", "Ftstravels@1")
                
                # Click login/submit
                # Try generic submit button or specific class
                try:
                    page.click("button[type='submit']", timeout=2000)
                except:
                    page.keyboard.press("Enter")
                
                print("Credentials submitted. Waiting for 2FA or Dashboard...")
                time.sleep(3)
                
                # Check for 2FA input
                if "login" in page.url or "mfa" in page.url or "verification" in page.url:
                     print("2FA / Verification page detected.")
                     print("Generating TOTP code...")
                     
                     # Secret extracted from user provided migration link
                     # Secret (Base32): PL5PTZ6JIBXER36Z7HPMP4ZBVS4VZOYU
                     totp = pyotp.TOTP("PL5PTZ6JIBXER36Z7HPMP4ZBVS4VZOYU")
                     code = totp.now()
                     print(f"Code generated: {code}")
                     
                     # Try to fill the code
                     # Inspecting common 2FA inputs
                     try:
                         # Wait for any input to be visible
                         page.wait_for_selector("input", timeout=10000)
                         
                         # Check for single input
                         code_input = page.locator("input[name='code'], input[name='otp'], input[placeholder*='code'], input[autocomplete='one-time-code'], input[type='tel'], input[inputmode='numeric']").first
                         
                         if code_input.is_visible():
                             print("Found single 2FA input field.")
                             code_input.fill(code)
                             # Submit
                             try:
                                 page.click("button[type='submit'], button:has-text('Verify'), button:has-text('Confirm')", timeout=2000)
                             except:
                                 page.keyboard.press("Enter")
                             print("2FA code submitted.")
                             
                         # Check for multiple inputs (6 boxes)
                         else:
                             inputs = page.locator("input[type='text'], input[type='tel'], input[inputmode='numeric']").all()
                             visible_inputs = [i for i in inputs if i.is_visible()]
                             
                             if len(visible_inputs) == 6:
                                 print("Found 6-digit input fields.")
                                 for i, digit in enumerate(code):
                                     visible_inputs[i].fill(digit)
                                 print("2FA code filled in 6 boxes.")
                                 # Usually auto-submits, or hit enter
                                 page.keyboard.press("Enter")
                             
                             # Last resort: Fill the first visible input found on the page
                             elif len(visible_inputs) > 0:
                                 print("Trying first visible input...")
                                 visible_inputs[0].fill(code)
                                 page.keyboard.press("Enter")
                             
                             else:
                                 print("Could not find 2FA input field automatically. Please enter manually: " + code)
                             
                     except Exception as e:
                         print(f"Error entering 2FA: {e}")
                         print(f"Please enter code manually: {code}")

        except Exception as e:
            print(f"Auto-login skipped/failed: {e}")
            print("Please log in manually.")

        # Wait until URL does NOT contain 'login'
        print("Waiting for login completion...")
        
        # Check if we already have a state
        if os.path.exists("gyg_auth_state.json"):
            print("Found saved session. Attempting to restore...")
            # We are already in a persistent context, so cookies might be there.
            # But let's check if we are logged in.
        
        while ("login" in page.url.lower() or "signin" in page.url.lower()) and not os.path.exists("confirm_login.txt"):
            print(f"Waiting... URL: {page.url} | Title: {page.title()}")
            time.sleep(2)
            
        if os.path.exists("confirm_login.txt"):
            print("Force start signal received!")
            os.remove("confirm_login.txt")
            
        print("Login detected/Confirmed! URL:", page.url)
        print("Waiting 5 seconds for dashboard to load fully...")
        time.sleep(5)
        
        # Save state explicitly
        context.storage_state(path="gyg_auth_state.json")
        print("Session saved to gyg_auth_state.json")
        
        for i, url in enumerate(urls):
            print(f"[{i+1}/{len(urls)}] Scraping: {url}")
            try:
                print("   > Navigating...")
                try:
                    page.goto(url, timeout=45000) # 45s timeout
                except Exception as e:
                    print(f"   > Navigation timeout/error: {e}")
                
                print("   > Page loaded (or timeout). Checking URL...")
                
                # Check if we were redirected to login
                if "login" in page.url:
                    print(f"⚠️ Session lost on {url}!")
                    print("PLEASE LOG IN AGAIN IN THE BROWSER.")
                    print("Waiting for you to be on the dashboard or product page...")
                    
                    while "login" in page.url:
                        time.sleep(2)
                        
                    print("Login restored! Saving new state...")
                    context.storage_state(path="gyg_auth_state.json")
                    
                    # Retry the URL
                    page.goto(url, timeout=45000)
                    time.sleep(3)

                print("   > Extracting data...")
                
                # --- ADVANCED EXTRACTION LOGIC ---
                trip_data = {
                    "url": url,
                    "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "title": page.title()
                }

                # Helper to get text safely with timeout
                def get_text(selector, timeout=2000):
                    try:
                        return page.locator(selector).first.inner_text(timeout=timeout).strip()
                    except:
                        return None

                # 1. Basic Info (Header Area)
                print("      - Basic Info...")
                try:
                    # Logic: Get parent text of the label
                    trip_data["product_id"] = page.get_by_text("Product Id:", exact=False).first.locator("..").text_content(timeout=2000).replace("Product Id:", "").strip()
                except: trip_data["product_id"] = None

                try:
                    trip_data["reference_code"] = page.get_by_text("Product Reference Code:", exact=False).first.locator("..").text_content(timeout=2000).replace("Product Reference Code:", "").strip()
                except: trip_data["reference_code"] = None
                    
                try:
                    trip_data["rating"] = page.get_by_text("Rating:", exact=False).first.locator("..").text_content(timeout=2000).replace("Rating:", "").strip()
                except: trip_data["rating"] = None

                # 2. Expand all buttons and accordions (Enhanced Logic)
                print("      - Expanding all sections...")
                try:
                    # 1. Accordions (aria-expanded='false')
                    accordions = page.locator("button[aria-expanded='false']").all()
                    for acc in accordions:
                        if acc.is_visible():
                            try: 
                                acc.scroll_into_view_if_needed()
                                acc.click(timeout=1000)
                                time.sleep(0.2)
                            except: pass

                    # 2. "See more" / "See all" buttons
                    # Using Regex to catch variations like "See all 15 inclusions"
                    expand_candidates = page.locator(r"text=/^See (more|all)/i").all()
                    for el in expand_candidates:
                        if el.is_visible():
                            try: 
                                el.scroll_into_view_if_needed()
                                el.click(timeout=1000)
                                time.sleep(0.2)
                            except: pass
                            
                    # 3. Dynamic text buttons (e.g., "See all 12 inclusions")
                    dynamic_expands = page.locator(r"text=/See all \d+ (inclusions|exclusions|highlights)/i").all()
                    for el in dynamic_expands:
                        if el.is_visible():
                            try: 
                                el.scroll_into_view_if_needed()
                                el.click(timeout=1000)
                                time.sleep(0.2)
                            except: pass
                            
                    # 4. Span buttons (p-button-label)
                    span_buttons = page.locator("span.p-button-label:has-text('See all')").all()
                    for sp in span_buttons:
                        if sp.is_visible():
                            try: 
                                sp.scroll_into_view_if_needed()
                                sp.click(timeout=1000)
                                time.sleep(0.2)
                            except: 
                                try: sp.locator("..").click(timeout=1000)
                                except: pass
                except: pass

                # 3. Descriptions (Enhanced Selectors based on HTML Analysis)
                print("      - Descriptions...")
                try:
                    # Short Description
                    # Try data-testid first (most robust)
                    trip_data["short_description"] = page.locator("[data-testid='pdp-details-main-information-short-desc']").inner_text(timeout=2000)
                except:
                    try:
                        # Fallback to sibling of 'Short description' label
                        trip_data["short_description"] = page.locator("xpath=//span[contains(text(), 'Short description')]/following-sibling::*").first.inner_text(timeout=1000)
                    except: trip_data["short_description"] = None

                try:
                    # Full Description
                    # Try data-testid
                    trip_data["full_description"] = page.locator("[data-testid='pdp-details-main-information-full-desc']").inner_text(timeout=2000)
                except:
                    try:
                         # Fallback to sibling of 'Full description' label
                        fd_section = page.locator("xpath=//span[contains(text(), 'Full description')]/following-sibling::*").first
                        trip_data["full_description"] = fd_section.inner_text(timeout=1000)
                    except: trip_data["full_description"] = None

                # 4. Highlights (Enhanced)
                print("      - Highlights...")
                try:
                    # Try data-testid (most robust)
                    hl_elems = page.locator("[data-testid='pdp-details-main-information-highlights'] li").all()
                    trip_data["highlights"] = [el.inner_text().strip() for el in hl_elems if el.inner_text().strip()]
                    
                    if not trip_data["highlights"]:
                        # Fallback: Generic siblings
                        hl_elems = page.locator("xpath=//span[contains(text(), 'Highlights')]/following-sibling::*//li").all()
                        trip_data["highlights"] = [el.inner_text().strip() for el in hl_elems if el.inner_text().strip()]
                except: trip_data["highlights"] = []

                # 5. Inclusions & Exclusions (Enhanced)
                print("      - Inclusions/Exclusions...")
                try:
                    # Inclusions
                    # Try data-testid or class specific to inclusions list
                    inc_elems = page.locator("[data-testid='pdp-details-main-information-inclusions'] li").all()
                    trip_data["inclusions"] = [el.inner_text().strip() for el in inc_elems if el.inner_text().strip()]
                    
                    if not trip_data["inclusions"]:
                        inc_elems = page.locator("xpath=//span[contains(text(), 'Inclusions')]/following-sibling::*//li").all()
                        trip_data["inclusions"] = [el.inner_text().strip() for el in inc_elems if el.inner_text().strip()]
                except: trip_data["inclusions"] = []

                try:
                    # Exclusions
                    exc_elems = page.locator("[data-testid='pdp-details-main-information-exclusions'] li").all()
                    trip_data["exclusions"] = [el.inner_text().strip() for el in exc_elems if el.inner_text().strip()]
                    
                    if not trip_data["exclusions"]:
                        exc_elems = page.locator("xpath=//span[contains(text(), 'Exclusions')]/following-sibling::*//li").all()
                        trip_data["exclusions"] = [el.inner_text().strip() for el in exc_elems if el.inner_text().strip()]
                except: trip_data["exclusions"] = []


                # 6. Important Info
                print("      - Important Info...")
                important_info = {}
                for label in ["Pet policy", "What mandatory items must the customer bring with them?", "Emergency contact number", "Know before you go"]:
                    try:
                        val = page.locator(f"xpath=//div[contains(text(), '{label}')]/following-sibling::div").first.inner_text(timeout=1000)
                        important_info[label] = val
                    except: pass
                trip_data["important_information"] = important_info

                # 7. Options
                print("      - Options...")
                trip_data["options"] = []
                try:
                    option_id_labels = page.get_by_text("Option ID", exact=True).all()
                    for label in option_id_labels:
                        try:
                            card = label.locator("..").locator("..") 
                            card_text = card.inner_text(timeout=1000)
                            option = {}
                            lines = card_text.split('\n')
                            for idx, line in enumerate(lines):
                                if line.strip() == "Title" and idx + 1 < len(lines): option['title'] = lines[idx+1]
                                elif line.strip() == "Reference code" and idx + 1 < len(lines): option['reference_code'] = lines[idx+1]
                                elif line.strip() == "Option ID" and idx + 1 < len(lines): option['option_id'] = lines[idx+1]
                                elif line.strip() == "Status" and idx + 1 < len(lines): option['status'] = lines[idx+1]
                                elif line.strip() == "Type" and idx + 1 < len(lines): option['type'] = lines[idx+1]
                            
                            if option.get('option_id'): trip_data["options"].append(option)
                        except: continue
                    
                    unique_options = {o['option_id']: o for o in trip_data["options"]}
                    trip_data["options"] = list(unique_options.values())
                except Exception as e: print(f"Error extracting options: {e}")

                # 8. Sidebar / Metadata
                print("      - Sidebar...")
                def get_sidebar_value(header_text):
                    try:
                        return page.locator(f"xpath=//div[contains(text(), '{header_text}')]/following-sibling::div").first.inner_text(timeout=1000)
                    except: return None

                trip_data["keywords"] = []
                try:
                    k_text = get_sidebar_value("Keywords")
                    if k_text: trip_data["keywords"] = k_text.split('\n')
                except: pass

                trip_data["transportation"] = get_sidebar_value("Transportation")
                trip_data["refund_policy"] = get_sidebar_value("Refund policy")
                
                trip_data["food_drinks"] = {}
                try:
                    fd_section = page.locator("xpath=//div[contains(text(), 'Food & Drinks')]/following-sibling::div").first
                    trip_data["food_drinks"]["raw"] = fd_section.inner_text(timeout=1000)
                except: pass

                # FULL TEXT BACKUP
                print("      - Full Text...")
                body_text = page.inner_text("body", timeout=5000)
                if "History" in body_text:
                    body_text = body_text.split("History\nDate")[0].strip()
                trip_data["full_text"] = body_text
                
                # --- REGEX FALLBACK (Enhanced based on concrete Full Text analysis) ---
                # The full_text contains all data, so we can rely on it if selectors fail.
                
                print("      - Running Regex Fallback...")
                
                if not trip_data.get("product_id"):
                    # Match: "Product Id: 522810"
                    m = re.search(r'Product Id:\s*(\d+)', body_text)
                    if m: trip_data["product_id"] = m.group(1)

                if not trip_data.get("reference_code"):
                    # Match: "Product Reference Code: 159159"
                    m = re.search(r'Product Reference Code:\s*(\w+)', body_text)
                    if m: trip_data["reference_code"] = m.group(1)

                if not trip_data.get("rating"):
                    # Match: "Rating:\n4.0 of 5"
                    m = re.search(r'Rating:\s*\n?\s*([\d.]+)\s*of\s*5', body_text)
                    if m: trip_data["rating"] = m.group(1)
                    
                if not trip_data.get("short_description"):
                    # Match: "Short description\n\nImmerse yourself..."
                    m = re.search(r'Short description\s*\n+(.+?)(?=\n+Full description)', body_text, re.DOTALL)
                    if m: trip_data["short_description"] = m.group(1).strip()
                    
                if not trip_data.get("full_description"):
                    # Match: "Full description\nDay 1:..." until "See less" or "Highlights"
                    m = re.search(r'Full description\s*\n+(.+?)(?=\n+See less|\n+Highlights)', body_text, re.DOTALL)
                    if m: 
                        desc = m.group(1).strip()
                        # Clean up "See less" if it got caught
                        desc = re.sub(r'\nSee less.*$', '', desc, flags=re.DOTALL)
                        trip_data["full_description"] = desc

                # Helper for list cleaning
                def clean_list_from_text(text_block):
                    cleaned = []
                    for line in text_block.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('See ') and line != 'See less' and len(line) > 2:
                            # Remove bullets
                            line = re.sub(r'^[•\-]\s*', '', line)
                            cleaned.append(line)
                    return cleaned

                if not trip_data.get("highlights"):
                    # Match: "Highlights\nCheck our..." until "See less"
                    m = re.search(r'Highlights\s*\n+(.+?)(?=\n+See less|\n+Inclusions)', body_text, re.DOTALL)
                    if m:
                        trip_data["highlights"] = clean_list_from_text(m.group(1))
                        
                if not trip_data.get("inclusions"):
                    # Match: "Inclusions\n• Meet..." until "See less" or "Exclusions"
                    m = re.search(r'Inclusions\s*\n+(.+?)(?=\n+See less|\n+Exclusions)', body_text, re.DOTALL)
                    if m:
                        trip_data["inclusions"] = clean_list_from_text(m.group(1))

                if not trip_data.get("exclusions"):
                    # Match: "Exclusions" header, ensuring it's NOT "Inclusions & Exclusions"
                    # We use negative lookbehind (?<!& ) to avoid matching "Inclusions & Exclusions"
                    m = re.search(r'(?<!& )Exclusions\s*\n+(.+?)(?=\n+See less|\n+Important information)', body_text, re.DOTALL)
                    if m:
                        exc_text = m.group(1)
                        if 'No exclusions added' not in exc_text:
                            trip_data["exclusions"] = clean_list_from_text(exc_text)

                if not trip_data.get("keywords"):
                     # Match: "Keywords\nHistory\n..." until "See all" or "Guide Information"
                     m = re.search(r'Keywords\s*\n+(.+?)(?=\n+See all|\n+Guide Information|\n+Transportation)', body_text, re.DOTALL)
                     if m:
                         kw_text = m.group(1)
                         trip_data["keywords"] = clean_list_from_text(kw_text)

                if not trip_data.get("transportation"):
                    # Match: "Transportation\nSightseeing cruise..." until "Refund policy"
                    m = re.search(r'Transportation\s*\n+(.+?)(?=\n+Refund policy)', body_text, re.DOTALL)
                    if m:
                        trans_text = m.group(1).replace('\n', ', ')
                        trip_data["transportation"] = trans_text.strip()


                # Options Extraction from Text (Critical Fallback)
                if not trip_data.get("options"):
                    print("      - Extracting options from text (Regex)...")
                    options = []
                    # Pattern from AI scarap.txt
                    option_pattern = r'Title\s*\n(.+?)\s*\nReference code\s*\n(.+?)\s*\nOption ID\s*\n(\d+)\s*\nStatus\s*\n(Active|Deactivated)(?:.*?\nType\s*\n(Private|Non-private))?'
                    matches = re.finditer(option_pattern, body_text, re.DOTALL)
                    for match in matches:
                        option = {
                            'title': match.group(1).strip(),
                            'reference_code': match.group(2).strip(),
                            'option_id': match.group(3).strip(),
                            'status': match.group(4).strip(),
                            'type': match.group(5).strip() if match.group(5) else None
                        }
                        options.append(option)
                    if options:
                        trip_data["options"] = options

                # Food & Drinks
                if not trip_data["food_drinks"]:
                    m = re.search(r'Food & Drinks\s*\nMeal\s*\n\s*Format\s*\n(.+?)(?:\nKeywords|$)', body_text, re.DOTALL)
                    if m:
                        food_text = m.group(1).strip()
                        lines = [l.strip() for l in food_text.split('\n') if l.strip()]
                        if len(lines) >= 2 and 'No food or drinks' not in food_text:
                            trip_data["food_drinks"] = {
                                'meal': lines[0].replace('\t', ' '),
                                'format': lines[1] if len(lines) > 1 else None
                            }


                
                data.append(trip_data)
                print(f"✅ Scraped: {trip_data.get('title', 'Unknown Title')} (ID: {trip_data.get('product_id')}) | Options: {len(trip_data['options'])}")
                
            except Exception as e:
                print(f"Failed to scrape {url}: {e}")
                
            # Generous delay as requested
            time.sleep(random.uniform(3.0, 6.0))
            
            # Save progress periodically
            if (i + 1) % 5 == 0:
                with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    
        context.close()
        
    # Final Save
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Done! Data saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    scrape_trips()
