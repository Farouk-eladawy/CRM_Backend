"""
Headout Tours Scraper - Full Extraction
Adapted from the user's Selenium code to run with Playwright for better compatibility.
Extracts all details from Headout.com including Itinerary, Inclusions, Exclusions, etc.
"""

import json
import time
import re
from datetime import datetime
import os
from playwright.sync_api import sync_playwright

class HeadoutToursScraper:
    def __init__(self):
        self.output_file = 'Headout_data.json'
        
    def extract_price(self, text):
        """Extract price from text"""
        match = re.search(r'\$(\d+)', text)
        return f"${match.group(1)}" if match else None
    
    def extract_duration(self, text):
        """Extract duration from text"""
        if 'hr' in text or 'hour' in text:
            match = re.search(r'(\d+)\s*hr', text)
            return f"{match.group(1)} hours" if match else text
        return text
    
    def scrape_tour_details(self, page, url):
        """Extract details for a single tour using Playwright"""
        try:
            print(f"\n{'='*80}")
            print(f"Scraping: {url}")
            print(f"{'='*80}")
            
            # Navigate
            try:
                page.goto(url, timeout=60000)
                # Random sleep to behave like a human
                time.sleep(3)
            except Exception as e:
                print(f"Navigation error: {e}")
                return None
            
            # Get full page text (similar to body.text in Selenium)
            page_text = page.inner_text("body")
            
            # Extract basic info
            tour_data = {
                'url': url,
                'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Title
            try:
                title = page.locator('h1').first.inner_text()
                tour_data['title'] = title
                print(f"✓ Title: {title[:50]}...")
            except:
                tour_data['title'] = None
            
            # Category & Badge
            try:
                # XPath from user code: //div[contains(text(), 'DAY TRIPS') or ...]
                # We add a few more categories just in case
                category_locator = page.locator("xpath=//div[contains(text(), 'DAY TRIPS') or contains(text(), 'MUSEUMS') or contains(text(), 'LANDMARKS') or contains(text(), 'CRUISES') or contains(text(), 'GUIDED TOURS')]").first
                if category_locator.is_visible():
                    tour_data['category'] = category_locator.inner_text()
                else:
                    tour_data['category'] = None
            except:
                tour_data['category'] = None
            
            # Price
            # User regex: r'from\s+\$\d+\s+\$(\d+)'
            # We adapt to handle Euro/other currencies if needed, but keeping user logic priority
            price_match = re.search(r'from\s+\$\d+\s+\$(\d+)', page_text)
            if price_match:
                tour_data['price_from'] = f"${price_match.group(1)}"
            else:
                price_match = re.search(r'from\s+\$(\d+)', page_text)
                if price_match:
                    tour_data['price_from'] = f"${price_match.group(1)}"
                else:
                    # Fallback for Euro or other currencies common on Headout
                    price_match_eur = re.search(r'(?:from|price)\s*([$€£]\s*\d+(?:[.,]\d+)?)', page_text, re.IGNORECASE)
                    tour_data['price_from'] = price_match_eur.group(1) if price_match_eur else None
            
            # Discount
            discount_match = re.search(r'(\d+)%\s*off', page_text)
            tour_data['discount'] = f"{discount_match.group(1)}% off" if discount_match else None
            
            # Rating
            rating_match = re.search(r'(\d+\.?\d*)\s*/5', page_text)
            tour_data['rating'] = float(rating_match.group(1)) if rating_match else None
            
            # Duration
            duration_match = re.search(r'Duration\s*\n\s*(\d+)\s*hr', page_text)
            if duration_match:
                tour_data['duration'] = f"{duration_match.group(1)} hours"
            else:
                duration_match = re.search(r'(\d+)\s*hours?', page_text)
                tour_data['duration'] = duration_match.group(0) if duration_match else "Flexible"
            
            # Features
            features = {}
            features['free_cancellation'] = 'Free cancellation' in page_text
            features['book_now_pay_later'] = 'Book now, pay later' in page_text
            features['guided_tour'] = 'Guided tour' in page_text
            features['transfers_included'] = 'Transfers included' in page_text
            features['hotel_pickup'] = 'Hotel pickup' in page_text
            features['meals_included'] = 'Meals included' in page_text
            features['skip_the_line'] = 'Skip' in page_text and 'line' in page_text
            tour_data['features'] = features
            
            # Highlights
            highlights = []
            # User Regex: r'Highlights\s*\n(.+?)(?:Inclusions|$)'
            highlights_section = re.search(r'Highlights\s*\n(.+?)(?:Inclusions|$)', page_text, re.DOTALL)
            if highlights_section:
                highlight_text = highlights_section.group(1)
                for line in highlight_text.split('\n'):
                    line = line.strip()
                    # Filter: length > 20, not starting with bullet (if raw text includes bullets)
                    # Playwright inner_text might strip some bullets or keep them.
                    if line and len(line) > 10 and line[0] not in ['I', 'H']: # 'I' for Inclusions header leak?
                         # Clean leading bullets
                        line = line.lstrip('•- ').strip()
                        if len(line) > 10:
                            highlights.append(line)
            tour_data['highlights'] = highlights[:10]
            
            # Inclusions
            inclusions = []
            inclusions_section = re.search(r'Inclusions\s*\n(.+?)(?:Exclusions|Itinerary|Cancellation)', page_text, re.DOTALL)
            if inclusions_section:
                inclusion_text = inclusions_section.group(1)
                for line in inclusion_text.split('\n'):
                    line = line.strip()
                    if line and len(line) > 5 and line not in ['Inclusions', 'based on option selected']:
                        inclusions.append(line.lstrip('•-✓ ').strip())
            tour_data['inclusions'] = inclusions[:20]
            
            # Exclusions
            exclusions = []
            exclusions_section = re.search(r'Exclusions\s*\n(.+?)(?:Itinerary|Cancellation|Your experience)', page_text, re.DOTALL)
            if exclusions_section:
                exclusion_text = exclusions_section.group(1)
                for line in exclusion_text.split('\n'):
                    line = line.strip()
                    if line and len(line) > 5:
                        exclusions.append(line.lstrip('•-✕ ').strip())
            tour_data['exclusions'] = exclusions[:15]
            
            # Itinerary
            itinerary = []
            itinerary_section = re.search(r'Itinerary(.+?)(?:Cancellation policy|Your experience)', page_text, re.DOTALL)
            if itinerary_section:
                itinerary_text = itinerary_section.group(1)
                # Extract stops
                # User Regex: r'(\d+)\.\s*([^\n]+)\s*(\d+)\s*min'
                stop_matches = re.findall(r'(\d+)\.\s*([^\n]+)\s*(\d+)\s*min', itinerary_text)
                for match in stop_matches:
                    itinerary.append({
                        'order': int(match[0]),
                        'name': match[1].strip(),
                        'duration': f"{match[2]} minutes"
                    })
            tour_data['itinerary'] = itinerary
            
            # Operating Hours
            operating_hours = {}
            hours_match = re.search(r'Operating hours\s*\n(.+?)(?:Know before|$)', page_text, re.DOTALL)
            if hours_match:
                hours_text = hours_match.group(1)
                if 'am' in hours_text.lower() or 'pm' in hours_text.lower():
                    operating_hours['info'] = hours_text.strip()[:200]
            tour_data['operating_hours'] = operating_hours
            
            # Know Before You Go
            know_before = {
                'what_to_bring': [],
                'whats_not_allowed': [],
                'accessibility': None
            }
            
            # What to bring
            bring_section = re.search(r'What to bring\s*\n(.+?)(?:What\'s not|Accessibility|$)', page_text, re.DOTALL)
            if bring_section:
                for line in bring_section.group(1).split('\n'):
                    line = line.strip()
                    if line and len(line) > 10 and line[0] not in ['W', 'A']:
                        know_before['what_to_bring'].append(line)
            
            # What's not allowed
            not_allowed_section = re.search(r'What\'s not allowed\s*\n(.+?)(?:Accessibility|Additional|$)', page_text, re.DOTALL)
            if not_allowed_section:
                for line in not_allowed_section.group(1).split('\n'):
                    line = line.strip()
                    if line and len(line) > 10:
                        know_before['whats_not_allowed'].append(line)
            
            # Accessibility
            accessibility_match = re.search(r'Accessibility\s*\n(.+?)(?:Additional|My tickets|$)', page_text, re.DOTALL)
            if accessibility_match:
                know_before['accessibility'] = accessibility_match.group(1).strip()[:300]
            
            tour_data['know_before_you_go'] = know_before
            
            # Cancellation Policy
            cancellation_match = re.search(r'Cancellation policy\s*\n(.+?)(?:Your experience|Reviews|$)', page_text, re.DOTALL)
            if cancellation_match:
                tour_data['cancellation_policy'] = cancellation_match.group(1).strip()[:200]
            else:
                tour_data['cancellation_policy'] = "These tickets can't be cancelled" if "can't be cancelled" in page_text else None
            
            # Your Experience
            experience_match = re.search(r'Your experience\s*\n(.+?)(?:Know before|Operating|$)', page_text, re.DOTALL)
            if experience_match:
                tour_data['your_experience'] = experience_match.group(1).strip()[:500]
            else:
                tour_data['your_experience'] = None
            
            print(f"✓ Scraped successfully!")
            print(f"  - Highlights: {len(tour_data['highlights'])}")
            print(f"  - Inclusions: {len(tour_data['inclusions'])}")
            print(f"  - Itinerary stops: {len(tour_data['itinerary'])}")
            
            return tour_data
            
        except Exception as e:
            print(f"✗ Error: {e}")
            return None
    
    def scrape_all_tours(self, urls):
        """Scrape all tours"""
        all_tours = []
        
        with sync_playwright() as p:
            # Launch browser
            user_data_dir = os.path.join(os.getcwd(), "headout_browser_data")
            context = p.firefox.launch_persistent_context(
                user_data_dir,
                headless=False,
                viewport={'width': 1280, 'height': 800}
            )
            page = context.pages[0] if context.pages else context.new_page()
            
            # Login check (Optional - reuse session if exists)
            # The user code didn't have login, but we use persistent context so it might work if logged in before.
            
            for i, url in enumerate(urls, 1):
                print(f"\n\n🎯 Processing Tour {i}/{len(urls)}")
                
                tour_data = self.scrape_tour_details(page, url)
                
                if tour_data:
                    all_tours.append(tour_data)
                
                # Save progress
                if i % 5 == 0:
                    self.save_to_json(all_tours)
            
            context.close()
        
        return all_tours
    
    def save_to_json(self, data):
        """Save data to JSON"""
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Data saved to {self.output_file}")


def read_urls_from_file(file_path):
    urls = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                match = re.search(r'(https?://[^\s]+)', line)
                if match:
                    urls.append(match.group(1))
    except Exception as e:
        print(f"Error reading file: {e}")
    return urls

def main():
    INPUT_FILE = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\Headout trips.csv"
    
    print(f"Reading URLs from {INPUT_FILE}...")
    tour_urls = read_urls_from_file(INPUT_FILE)
    print(f"Found {len(tour_urls)} URLs.")
    
    if not tour_urls:
        print("No URLs found. Exiting.")
        return

    # Create scraper
    scraper = HeadoutToursScraper()
    
    try:
        data = scraper.scrape_all_tours(tour_urls)
        scraper.save_to_json(data)
    except Exception as e:
        print(f"Fatal Error: {e}")

if __name__ == "__main__":
    main()
