import json
import time
import schedule
import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# رابط بحث جوجل المباشر الذي يظهر فيه الملف التجاري للشركة (كما في صورتك)
MAPS_URL = "https://www.google.com/search?q=FTS+Travels"
OUTPUT_FILE = "google_reviews_scraped.json"

def scrape_reviews():
    logging.info("بدأ تشغيل سكريبت جلب التقييمات من جوجل...")
    reviews_data = []
    
    with sync_playwright() as p:
        # تشغيل المتصفح في الخلفية (Headless)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="en-US")
        page = context.new_page()
        
        try:
            page.goto(MAPS_URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            time.sleep(3)
            
            # محاولة النقر على زر "Google reviews" في الجانب الأيمن (Knowledge Panel)
            try:
                # هذا هو العنصر الذي يحتوي على عدد التقييمات ويفتح نافذة التقييمات
                reviews_link = page.locator("a[data-async-trigger='reviewDialog']").first
                if reviews_link.is_visible():
                    reviews_link.click()
                    logging.info("تم فتح نافذة التقييمات بنجاح.")
                    time.sleep(5)  # انتظار تحميل النافذة المنبثقة
                else:
                    logging.warning("لم يتم العثور على رابط التقييمات في صفحة البحث.")
            except Exception as e:
                logging.warning(f"خطأ أثناء محاولة فتح التقييمات: {e}")

            # استخراج التقييمات من النافذة المنبثقة
            # هذا الـ Class (gws-localreviews__google-review) هو الشائع في نوافذ التقييمات المنبثقة في بحث جوجل
            review_elements = page.locator(".gws-localreviews__google-review").all()
            logging.info(f"تم العثور على {len(review_elements)} تقييمات في النافذة.")
            
            for el in review_elements[:20]:  # جلب أحدث 20 تقييم
                try:
                    # استخراج اسم الكاتب
                    author_locator = el.locator(".TSUbDb a")
                    author = author_locator.inner_text() if author_locator.count() > 0 else "Unknown"
                    
                    # استخراج عدد النجوم
                    rating_locator = el.locator(".Fam1ne")
                    rating = 5
                    if rating_locator.count() > 0:
                        aria_label = rating_locator.first.get_attribute("aria-label")
                        if aria_label:
                            # استخراج الرقم من النص (مثل "Rated 5.0 out of 5")
                            import re
                            match = re.search(r'(\d+[\.,]?\d*)', aria_label)
                            if match:
                                rating = int(float(match.group(1)))
                    
                    # استخراج التاريخ
                    date_locator = el.locator(".dehysf")
                    date_str = date_locator.inner_text() if date_locator.count() > 0 else ""
                    
                    # استخراج نص التقييم
                    # أحياناً يكون هناك زر "More" يجب النقر عليه لقراءة النص كاملاً
                    more_btn = el.locator(".review-more-link")
                    if more_btn.count() > 0 and more_btn.first.is_visible():
                        more_btn.first.click()
                        
                    text_locator = el.locator(".Jtu6Td span").last
                    content = text_locator.inner_text() if text_locator.count() > 0 else ""
                    
                    # توليد ID عشوائي إذا لم يكن موجوداً
                    import uuid
                    review_id = str(uuid.uuid4())[:8]
                    
                    reviews_data.append({
                        "id": review_id,
                        "author": author,
                        "rating": rating,
                        "date": date_str,
                        "content": content,
                        "platform": "google",
                        "isNew": True
                    })
                except Exception as e:
                    logging.error(f"خطأ أثناء تحليل أحد التقييمات: {e}")
                    
        except Exception as e:
            logging.error(f"حدث خطأ أثناء تحميل الصفحة أو سحب البيانات: {e}")
        finally:
            browser.close()
            
    # حفظ البيانات في ملف JSON
    if reviews_data:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(reviews_data, f, ensure_ascii=False, indent=4)
        logging.info(f"✅ تم حفظ {len(reviews_data)} تقييم بنجاح في ملف {OUTPUT_FILE}")
    else:
        logging.warning("⚠️ لم يتم العثور على تقييمات ليتم حفظها.")

def job():
    scrape_reviews()

if __name__ == "__main__":
    # تشغيل السكريبت مرة واحدة فوراً للتأكد من عمله
    scrape_reviews()
    
    # جدولة السكريبت ليعمل كل ساعة في الخلفية
    logging.info("تم تفعيل المجدول (Scheduler). السكريبت سيعمل كل ساعة في الخلفية...")
    schedule.every(1).hours.do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)