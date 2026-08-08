import json
from bs4 import BeautifulSoup
import sys
import re
from lxml import html
import time
import random

# Try to import Playwright, handle if not installed
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Try to import Stealth
try:
    from playwright_stealth import Stealth
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False

# ============== Configuration / الإعدادات ==============

VIATOR_SELECTORS = { 
    # ============== معلومات أساسية ============== 
    "title": "h1",  # عنوان الرحلة 
    "location": "div[class*='location']", 
    "product_code": "span:contains('Product code')", # Adjusted to be findable, logic handles sibling
    
    # ============== السعر ============== 
    "price": { 
        "from_text": "span:contains('From')", 
        "price_value": "span[class*='price'], div[data-test-id='price-from'] span", 
        "currency": "span[class*='currency']", 
        "per_person": "span:contains('per person')", 
        "original_price": "span[class*='original-price'], s", 
        "discount_badge": "span[class*='discount'], div[class*='badge']" 
    }, 
    
    # ============== المدة والتفاصيل الأساسية ============== 
    "duration": "div:contains('hours'), span:contains('hours'), li:contains('hours')", 
    "start_time": "div:contains('Start time'), h3:contains('Start time')",
    "languages": "div:contains('Offered in:'), span:contains('English')", 
    
    # ============== الميزات ============== 
    "features": { 
        "pickup_offered": "span:contains('Pickup offered'), div:contains('Pickup offered')", 
        "mobile_ticket": "span:contains('Mobile ticket')", 
        "group_discounts": "span:contains('Group discounts')", 
        "wheelchair_accessible": "span:contains('wheelchair')", 
        "free_cancellation": "span:contains('Free cancellation'), button:contains('Free cancellation')" 
    }, 
    
    # ============== Overview / الوصف ============== 
    "overview": { 
        "section": "section[aria-labelledby='overview'], div[id*='overview']", 
        "description": "div[class*='overview'] p, section[aria-labelledby='overview'] p", 
        "highlights": "ul[class*='highlight'] li, div[class*='highlight'] li" 
    }, 
    
    # ============== What's Included ============== 
    "whats_included": { 
        "button": "button:contains('What\\'s Included'), h2:contains('What\\'s Included')", 
        "included_items": "div[class*='included'] li, ul li:has(svg[class*='check'])", 
        "not_included_items": "div[class*='not-included'] li, ul li:has(svg[class*='x'])", 
        "additional_costs": "span:contains('per person'), span:contains('$')" 
    }, 
    
    # ============== Itinerary / المسار ============== 
    "itinerary": { 
        "button": "button:contains('Itinerary'), h2:contains('Itinerary')", 
        "stops": "div[class*='itinerary'] > div", 
        "stop_name": "h3, strong, span[class*='title']", 
        "stop_type": "span:contains('Pass By'), span:contains('Stop'), span:contains('Admission')", 
        "stop_description": "p, div[class*='description']" 
    }, 
    
    # ============== Meeting & Pickup ============== 
    "meeting_pickup": { 
        "section": "section:contains('Meeting and Pickup'), div[id*='pickup']", 
        "pickup_points": "div[class*='pickup'] input, select", 
        "pickup_details": "div:contains('Hotel pickup'), p:contains('pickup')", 
        "start_time": "span:contains('8:00'), span:contains('am')" 
    }, 
    
    # ============== Additional Info ============== 
    "additional_info": { 
        "button": "button:contains('Additional Info')", 
        "items": "ul li, div[class*='additional'] p", 
        "confirmation": "li:contains('Confirmation')", 
        "accessibility": "li:contains('wheelchair'), li:contains('accessible')", 
        "restrictions": "li:contains('Not recommended'), li:contains('No heart')" 
    }, 
    
    # ============== Supplier ============== 
    "supplier": { 
        "name": "button:contains('Supplied by'), span:contains('Supplied by')", 
        "rating": "span[class*='rating'], div[class*='review'] span" 
    }, 
    
    # ============== Cancellation Policy ============== 
    "cancellation_policy": { 
        "section": "div:contains('Cancellation Policy'), h2:contains('Cancellation')", 
        "description": "p:contains('cancel'), p:contains('refund')", 
        "show_more": "button:contains('Show more')" 
    }, 
    
    # ============== Reviews ============== 
    "reviews": { 
        "rating": "span[class*='rating'], div[data-test-id='rating']", 
        "count": "span:contains('reviews'), span:contains('review')", 
        "stars": "svg[class*='star']" 
    }, 
    
    # ============== Images ============== 
    "images": { 
        "main_image": "div[class*='gallery'] img, picture img", 
        "thumbnails": "button img, div[class*='thumbnail'] img", 
        "all_images": "img[alt*='tour'], img[alt*='Tour']" 
    }, 
    
    # ============== Booking Options ============== 
    "booking": { 
        "date_selector": "input[id*='date'], button:contains('Date')", 
        "travelers_selector": "input[aria-label*='travelers'], select[id*='traveler']", 
        "check_availability": "button:contains('Check Availability')", 
        "reserve_button": "button:contains('Reserve'), button:contains('Book')" 
    } 
} 

# ============== XPath Selectors (أكثر دقة) ============== 

VIATOR_XPATH = { 
    "title": "//h1", 
    "location": "//span[contains(text(), ', Egypt')] | //div[contains(@class, 'location')]", 
    "product_code": "//text()[contains(., 'Product code:')]/following-sibling::text()[1]", 
    
    "price_value": "//span[contains(text(), '$')] | //div[@data-test-id='price-from']//span", 
    
    "duration": "//*[contains(text(), 'hours') and (contains(text(), '8') or contains(text(), 'approx'))]", 
    
    "overview_description": "//section[@aria-labelledby='overview']//p | //div[contains(@class, 'overview')]//p", 
    
    "whats_included_list": "//div[.//h2[contains(text(), \"What's Included\")]]//li[.//svg[contains(@class, 'check')]]", 
    "whats_not_included_list": "//div[.//h2[contains(text(), \"What's Included\")]]//li[.//svg[contains(@class, 'x')]]", 
    
    "itinerary_stops": "//div[.//h2[contains(text(), 'Itinerary')]]//div[contains(@class, 'stop')]", 
    "itinerary_stop_names": ".//h3 | .//strong", 
    "itinerary_stop_descriptions": ".//p[not(contains(@class, 'type'))]", 
    
    "additional_info_items": "//div[.//h2[contains(text(), 'Additional Info')]]//li", 
    
    "supplier_name": "//button[contains(text(), 'Supplied by')] | //span[contains(text(), 'Supplied by')]/following-sibling::button", 
    
    "cancellation_text": "//div[.//h2[contains(text(), 'Cancellation')]]//p", 
    
    "free_cancellation": "//*[contains(text(), 'Free cancellation')] | //*[contains(text(), 'cancel up to 24 hours')]" 
}

# ============== Helpers / دوال مساعدة ==============

def clean_text(text):
    if text:
        return re.sub(r'\s+', ' ', text).strip()
    return ""

def get_xpath_text(tree, xpath_query):
    try:
        elements = tree.xpath(xpath_query)
        if elements:
            if isinstance(elements[0], str):
                return clean_text(elements[0])
            return clean_text(elements[0].text_content())
    except Exception as e:
        pass
    return None

def get_xpath_list(tree, xpath_query):
    results = []
    try:
        elements = tree.xpath(xpath_query)
        for el in elements:
            if isinstance(el, str):
                results.append(clean_text(el))
            else:
                results.append(clean_text(el.text_content()))
    except:
        pass
    return results

def get_css_text(soup, selector):
    if not selector: return None
    # Fix :contains for BS4
    bs4_selector = selector.replace(":contains", ":-soup-contains")
    try:
        element = soup.select_one(bs4_selector)
        if element:
            return clean_text(element.text)
    except Exception as e:
        pass
    return None

def get_css_list(soup, selector):
    if not selector: return []
    bs4_selector = selector.replace(":contains", ":-soup-contains")
    results = []
    try:
        elements = soup.select(bs4_selector)
        for el in elements:
            results.append(clean_text(el.text))
    except:
        pass
    return results

# ============== Fetching Logic / منطق التحميل ==============

def fetch_page_content(url):
    if not PLAYWRIGHT_AVAILABLE:
        print("Error: Playwright is not installed. Please run: pip install playwright")
        print("خطأ: مكتبة Playwright غير مثبتة.")
        return None

    print(f"Fetching {url}...")
    print("Launching browser (this may take a few seconds)... / جاري تشغيل المتصفح...")

    with sync_playwright() as p:
        # Launch options
        browser = p.chromium.launch(
            headless=True, # Set to False if you want to see the browser / اجعله False لرؤية المتصفح
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--window-position=0,0',
                '--ignore-certifcate-errors',
                '--ignore-certifcate-errors-spki-list',
            ]
        )
        
        # Context with realistic User Agent and Viewport
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
            has_touch=False,
            is_mobile=False,
            device_scale_factor=1,
        )

        page = context.new_page()

        # Apply Stealth if available
        if STEALTH_AVAILABLE:
            stealth = Stealth()
            stealth.apply_stealth_sync(page)

        try:
            # Go to page
            page.goto(url, timeout=90000, wait_until="domcontentloaded")
            
            # Wait for dynamic content / انتظار المحتوى الديناميكي
            print("Page loaded, waiting for content... / تم تحميل الصفحة، جاري انتظار المحتوى...")
            time.sleep(random.uniform(3, 6))
            
            # Scroll down to trigger lazy loading / التمرير لأسفل لتحميل الصور والمحتوى
            page.mouse.wheel(0, 1000)
            time.sleep(2)
            page.mouse.wheel(0, 2000)
            time.sleep(2)
            
            # Check for CAPTCHA title
            title = page.title()
            if "captcha" in title.lower() or "datadome" in title.lower() or "access denied" in title.lower():
                print("Warning: Possible CAPTCHA detected in title. / تحذير: احتمال وجود كابتشا.")
            
            content = page.content()
            return content
            
        except Exception as e:
            print(f"Error fetching page: {e}")
            return None
        finally:
            browser.close()

# ============== Main Extraction / الاستخراج الرئيسي ==============

def extract_from_html(html_content):
    soup = BeautifulSoup(html_content, 'lxml')
    tree = html.fromstring(html_content)
    
    data = {}

    # 1. JSON-LD (Structured Data) - First Priority
    # محاولة العثور على البيانات الهيكلية أولاً
    json_ld = None
    scripts = soup.find_all('script', type='application/ld+json')
    for script in scripts:
        try:
            ld = json.loads(script.string)
            if '@type' in ld and ld['@type'] == 'Product':
                json_ld = ld
                break
        except:
            continue

    # 2. Extract Fields using Selectors
    
    # --- Title ---
    data['tour_name'] = get_xpath_text(tree, VIATOR_XPATH['title']) or \
                        get_css_text(soup, VIATOR_SELECTORS['title']) or \
                        (json_ld.get('name') if json_ld else "N/A")

    # --- URL ---
    if json_ld and 'url' in json_ld:
        data['url'] = json_ld['url']
    else:
        canonical = soup.find('link', rel='canonical')
        data['url'] = canonical['href'] if canonical else "N/A"

    # --- Product Code ---
    data['product_code'] = get_xpath_text(tree, VIATOR_XPATH['product_code'])
    if not data['product_code'] or data['product_code'] == "N/A":
        # Fallback to Regex from URL
        if data['url'] != "N/A":
            match = re.search(r'(\d+P\d+)', data['url'])
            if match:
                data['product_code'] = match.group(1)

    # --- Location ---
    data['location'] = get_xpath_text(tree, VIATOR_XPATH['location']) or \
                       get_css_text(soup, VIATOR_SELECTORS['location']) or "Cairo, Egypt"

    # --- Rating & Reviews ---
    if json_ld and 'aggregateRating' in json_ld:
        data['rating'] = str(json_ld['aggregateRating'].get('ratingValue', 0.0))
        data['number_of_reviews'] = str(json_ld['aggregateRating'].get('reviewCount', 0))
    else:
        data['rating'] = get_css_text(soup, VIATOR_SELECTORS['reviews']['rating']) or "0.0"
        data['number_of_reviews'] = get_css_text(soup, VIATOR_SELECTORS['reviews']['count']) or "0"

    # --- Price ---
    # Try JSON-LD first for structured price
    if json_ld and 'offers' in json_ld:
        data['price_from'] = f"${json_ld['offers'].get('lowPrice', 0)}"
        data['price_unit'] = "per person"
    else:
        data['price_from'] = get_xpath_text(tree, VIATOR_XPATH['price_value']) or \
                             get_css_text(soup, VIATOR_SELECTORS['price']['price_value']) or "N/A"
        data['price_unit'] = get_css_text(soup, VIATOR_SELECTORS['price']['per_person']) or "per person"

    # --- Duration ---
    data['duration'] = get_xpath_text(tree, VIATOR_XPATH['duration']) or \
                       get_css_text(soup, VIATOR_SELECTORS['duration']) or "N/A"

    # --- Highlights ---
    # From Overview section usually
    data['highlights'] = get_css_list(soup, VIATOR_SELECTORS['overview']['highlights'])

    # --- What's Included ---
    data['whats_included'] = get_xpath_list(tree, VIATOR_XPATH['whats_included_list']) or \
                             get_css_list(soup, VIATOR_SELECTORS['whats_included']['included_items'])

    # --- What's Not Included ---
    data['whats_not_included'] = get_xpath_list(tree, VIATOR_XPATH['whats_not_included_list']) or \
                                 get_css_list(soup, VIATOR_SELECTORS['whats_included']['not_included_items'])

    # --- Meeting Point ---
    data['meeting_point'] = {
        "pickup_offered": bool(get_css_text(soup, VIATOR_SELECTORS['features']['pickup_offered'])),
        "pickup_details": get_css_text(soup, VIATOR_SELECTORS['meeting_pickup']['pickup_details']) or "See details on page"
    }

    # --- Itinerary ---
    itinerary = []
    # Try XPath extraction for itinerary
    # This is more complex as it's a list of objects
    try:
        stops_elements = tree.xpath(VIATOR_XPATH['itinerary_stops'])
        if not stops_elements:
             # Fallback to CSS
             pass
        
        for idx, stop_el in enumerate(stops_elements, 1):
            name_el = stop_el.xpath(VIATOR_XPATH['itinerary_stop_names'])
            desc_el = stop_el.xpath(VIATOR_XPATH['itinerary_stop_descriptions'])
            
            name = clean_text(name_el[0].text_content()) if name_el else f"Stop {idx}"
            desc = clean_text(desc_el[0].text_content()) if desc_el else ""
            
            step = {
                "stop": str(idx),
                "location": "Location",
                "time": "Time",
                "description": f"{name} - {desc}",
                "duration": "See description",
                "admission": "Admission info"
            }
            itinerary.append(step)
    except Exception as e:
        print(f"Error parsing itinerary with XPath: {e}")

    if not itinerary:
        # Fallback to simple CSS extraction
        stops = soup.select(VIATOR_SELECTORS['itinerary']['stops'])
        for idx, stop in enumerate(stops, 1):
            name = get_css_text(stop, VIATOR_SELECTORS['itinerary']['stop_name'])
            desc = get_css_text(stop, VIATOR_SELECTORS['itinerary']['stop_description'])
            itinerary.append({
                "stop": str(idx),
                "location": "Location",
                "time": "Time",
                "description": f"{name} - {desc}",
                "duration": "Duration",
                "admission": "Admission"
            })
            
    data['itinerary'] = itinerary

    # --- Additional Info ---
    data['additional_info'] = get_xpath_list(tree, VIATOR_XPATH['additional_info_items']) or \
                              get_css_list(soup, VIATOR_SELECTORS['additional_info']['items'])

    # --- Supplier ---
    data['supplier'] = get_xpath_text(tree, VIATOR_XPATH['supplier_name']) or \
                       get_css_text(soup, VIATOR_SELECTORS['supplier']['name']) or "FTS Travels"
                       
    # --- Cancellation Policy ---
    data['cancellation_policy'] = get_xpath_text(tree, VIATOR_XPATH['cancellation_text']) or \
                                  get_css_text(soup, VIATOR_SELECTORS['cancellation_policy']['description'])

    return data

if __name__ == "__main__":
    input_arg = "viator_page.html"
    if len(sys.argv) > 1:
        input_arg = sys.argv[1]
    
    content = None
    
    # Check if input is a URL / التحقق مما إذا كان المدخل رابطاً
    if input_arg.startswith('http'):
        content = fetch_page_content(input_arg)
        if not content:
            sys.exit(1)
    else:
        # It's a file / إنه ملف
        try:
            with open(input_arg, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"File {input_arg} not found. / الملف غير موجود.")
            print("Usage: python scraper.py <url_or_file_path>")
            sys.exit(1)

    if content:
        if "captcha" in content.lower() and len(content) < 5000:
                print("Error: The content seems to be a CAPTCHA page. / خطأ: يبدو أن المحتوى هو صفحة تحقق.")
        else:
            result = extract_from_html(content)
            print(json.dumps(result, indent=2, ensure_ascii=False))
