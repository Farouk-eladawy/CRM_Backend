from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import json, time, re, os, random
from datetime import datetime

# --- Load URLs from file ---
INPUT_FILE = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\Viator links.txt"
TOUR_URLS = []

if os.path.exists(INPUT_FILE):
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            
            # Extract URL if line contains tab or spaces
            parts = line.split('http')
            if len(parts) > 1:
                url = 'http' + parts[1].strip()
            elif line.startswith('http'):
                url = line
            else:
                continue
                
            TOUR_URLS.append(url)
else:
    # Fallback to provided list if file fails
    TOUR_URLS = [
        "https://www.viator.com/tours/Luxor/Private-Full-Day-Luxor-Tour-Customize-Your-Adventure/d826-14976P141",
        "https://www.viator.com/tours/Marsa-Alam/Cairo-Day-Tour-by-Plane-from-Marsa-Alam/d25556-14976P140"
    ]

class ViatorScraper:
    def __init__(self, headless=True):
        opts = Options()
        if headless:
            opts.add_argument('--headless')
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        opts.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Additional Anti-Detection
        opts.add_argument('--disable-blink-features=AutomationControlled')
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=opts)
        self.driver.maximize_window()
        self.tours_data = []
        
    def close_popups(self):
        """إغلاق النوافذ المنبثقة"""
        try:
            # Cookie Consent
            btn = self.driver.find_element(By.ID, "onetrust-accept-btn-handler")
            btn.click()
            time.sleep(1)
        except:
            pass
     
    def safe_get(self, xpath, default=None):
        """استخراج نص بأمان"""
        try:
            elem = self.driver.find_element(By.XPATH, xpath)
            return elem.text.strip() if elem.text else default
        except:
            return default
     
    def safe_gets(self, xpath):
        """استخراج نصوص متعددة"""
        try:
            elems = self.driver.find_elements(By.XPATH, xpath)
            return [e.text.strip() for e in elems if e.text.strip()]
        except:
            return []
     
    def extract_product_code(self):
        """استخراج كود المنتج"""
        try:
            # Try text search
            text = self.safe_get("//*[contains(text(), 'Product code:')]")
            if text:
                return text.replace("Product code:", "").strip()
            
            # Fallback to URL
            match = re.search(r'(\d+P\d+)', self.driver.current_url)
            return match.group(1) if match else None
        except: return None
     
    def extract_price(self):
        """استخراج السعر"""
        text = self.safe_get("//span[contains(text(), '$')]")
        if text:
            match = re.search(r'\$(\d+(?:\.\d+)?)', text)
            if match:
                return {"amount": float(match.group(1)), "currency": "USD"}
        
        # Fallback for 'From'
        text = self.safe_get("//div[@data-test-id='price-from']//span")
        if text:
             match = re.search(r'(\d+(?:\.\d+)?)', text)
             if match:
                 return {"amount": float(match.group(1)), "currency": "USD"}
        return None
     
    def extract_rating(self):
        """استخراج التقييم"""
        text = self.safe_get("//*[contains(text(), 'Review')]")
        if text:
            nums = re.findall(r'(\d+\.?\d*)', text)
            if len(nums) >= 2:
                return {"score": float(nums[0]), "reviews": int(nums[1].replace(',', ''))}
        return {"score": 0.0, "reviews": 0}
     
    def extract_features(self):
        """استخراج الميزات"""
        src = self.driver.page_source.lower()
        return {
            "pickup": "pickup offered" in src,
            "mobile_ticket": "mobile ticket" in src,
            "free_cancellation": "free cancellation" in src,
            "private": "private" in src
        }

    def extract_whats_included(self):
        """استخراج ما يشمله السعر"""
        try:
            # Expand 'See all'
            btns = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'See')]")
            for btn in btns:
                try: btn.click()
                except: pass
            time.sleep(1)
        except:
            pass
        
        # Try finding the section
        items = self.safe_gets("//div[.//h2[contains(text(), \"What's Included\")]]//li[.//svg[contains(@class, 'check')]]")
        
        if not items:
             items = self.safe_gets("//h2[contains(text(), 'Included')]/following-sibling::*//li")
             
        included = []
        for item in items[:15]:
            if not any(x in item.lower() for x in ['entrance', 'lunch', 'gratuities', 'drinks']):
                included.append(item)
        return included if included else ["See website for details"]
    
    def extract_itinerary(self):
        """استخراج المسار"""
        stops = self.safe_gets("//h2[contains(text(), 'Itinerary')]/following-sibling::*//h3")
        if not stops:
             stops = self.safe_gets("//div[contains(@class, 'timeline-item')]//span[contains(@class, 'title')]")
        
        itinerary = []
        for stop in stops[:10]:
            itinerary.append({"stop": stop, "type": "Stop"})
            
        return itinerary if itinerary else []
    
    def scrape_tour(self, url):
        """استخراج بيانات رحلة واحدة"""
        print(f"\n🔄 {url.split('/')[-1][:40]}...")
        
        try:
            self.driver.get(url)
            time.sleep(random.uniform(3, 5))
            self.close_popups()
            
            # التمرير لتحميل المحتوى
            self.driver.execute_script("window.scrollTo(0, 800);")
            time.sleep(2)
            self.driver.execute_script("window.scrollTo(0, 1600);")
            time.sleep(1)
            
            title = self.safe_get("//h1")
            
            # Check for Cloudflare/Block
            if not title and ("challenge" in self.driver.title.lower() or "just a moment" in self.driver.title.lower()):
                print("⚠️ Cloudflare Challenge Detected!")
                time.sleep(10)
                title = self.safe_get("//h1") # Retry
            
            data = {
                "tour_info": {
                    "platform": "Viator",
                    "url": url,
                    "product_code": self.extract_product_code(),
                    "title": title or "Unknown Title",
                    "location": "Egypt",
                    "category": "Tours",
                    "breadcrumb": ["Home", "Egypt"]
                },
                "pricing": {
                    "price_from": self.extract_price().get('amount') if self.extract_price() else 0.0,
                    "currency": "USD",
                    "price_unit": "per person",
                    "discounted_rates_for_kids": True,
                    "lowest_price_guarantee": True
                },
                "overview": {
                    "description": self.safe_get("//h2[contains(text(),'Overview')]/following-sibling::div") or f"Experience {title}",
                    "duration": self.safe_get("//*[contains(text(),'hour') or contains(text(),'day')]") or "Flexible",
                    "start_time": self.safe_get("//*[contains(text(),'Start time')]/following-sibling::*") or "Varies",
                    "languages": ["English"]
                },
                "features": {
                    "pickup_offered": self.extract_features()['pickup'],
                    "mobile_ticket": self.extract_features()['mobile_ticket'],
                    "wheelchair_accessible": False,
                    "private_tour": self.extract_features()['private']
                },
                "whats_included": self.extract_whats_included(),
                "whats_not_included": ["Gratuities"],
                "meeting_and_pickup": {
                    "pickup_points": "Select a pickup point",
                    "pickup_details": "Check voucher",
                    "start_time": "Varies"
                },
                "itinerary": self.extract_itinerary(),
                "additional_info": ["Confirmation received at booking"],
                "supplier": {
                    "name": self.safe_get("//*[contains(text(),'Supplied by')]/following-sibling::*") or "FTS Travels"
                },
                "cancellation_policy": {
                    "description": "Free cancellation up to 24 hours before." if self.extract_features()['free_cancellation'] else "Check policy.",
                    "free_cancellation": "24 hours" if self.extract_features()['free_cancellation'] else "Check details"
                },
                "booking_options": {
                    "reserve_now_pay_later": True,
                    "reserve_now_pay_later_description": "Secure your spot"
                }
            }
            
            print(f"✅ تم: {data['tour_info']['title'][:50]}")
            return data
            
        except Exception as e:
            print(f"❌ خطأ: {str(e)[:50]}")
            return None
    
    def scrape_batch(self, start_idx, end_idx):
        """استخراج مجموعة من الرحلات"""
        batch_urls = TOUR_URLS[start_idx:end_idx]
        batch_data = []
        
        print(f"\n{'='*60}")
        print(f"📦 استخراج الرحلات {start_idx+1} إلى {end_idx}")
        print(f"{'='*60}")
        
        for i, url in enumerate(batch_urls, start=start_idx+1):
            try:
                data = self.scrape_tour(url)
                if data:
                    batch_data.append(data)
                print(f"✅ {i}/{len(TOUR_URLS)} تم")
            except Exception as e:
                print(f"❌ {i}/{len(TOUR_URLS)} فشل: {str(e)[:30]}")
            
            time.sleep(random.uniform(2, 4))  # تأخير عشوائي
        
        return batch_data
    
    def save_to_json(self, data, filename):
        """حفظ البيانات في ملف JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 تم الحفظ في: {filename}")
    
    def run_all_batches(self):
        """تشغيل جميع المجموعات"""
        all_data = []
        batch_size = 10
        total_batches = (len(TOUR_URLS) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start = batch_num * batch_size
            end = min(start + batch_size, len(TOUR_URLS))
            
            print(f"\n🔹 المجموعة {batch_num + 1}/{total_batches}")
            batch_data = self.scrape_batch(start, end)
            all_data.extend(batch_data)
            
            # حفظ الملف النهائي (تحديث مستمر)
            self.save_to_json(all_data, r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\Viator_data.json")
        
        print(f"\n{'='*60}")
        print(f"🎉 اكتمل! تم استخراج {len(all_data)} رحلة")
        print(f"{'='*60}")
        
        self.driver.quit()
        return all_data

def print_summary(data):
    """طباعة ملخص البيانات"""
    print(f"\n{'='*60}")
    print(f"📊 ملخص الاستخراج")
    print(f"{'='*60}")
    print(f"📦 المجموع: {len(data)}")
    print(f"{'='*60}\n")

def main():
    """الدالة الرئيسية"""
    print(f"""
    ╔═══════════════════════════════════════════════════════╗
    ║         Viator Tours Scraper v2.0 (Selenium)          ║
    ║         استخراج بيانات الرحلات من Viator              ║
    ║                 {len(TOUR_URLS)} رحلة                              ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    
    # الوضع الافتراضي: استخراج الكل بدون سؤال (لتعمل في الخلفية)
    print("\n⏳ جاري استخراج جميع الرحلات...")
    scraper = ViatorScraper(headless=True)
    
    try:
        data = scraper.run_all_batches()
        print_summary(data)
    except KeyboardInterrupt:
        print("\n\n⚠️ تم إيقاف العملية بواسطة المستخدم")
        scraper.driver.quit()
    except Exception as e:
        print(f"\n❌ خطأ: {str(e)}")
        scraper.driver.quit()
    
    print("\n👋 انتهى البرنامج")

if __name__ == "__main__":
    main()
