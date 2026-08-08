import os
import json
import time
import random
import logging
import pyotp
from playwright.sync_api import sync_playwright

# استيراد العقل (ai_agent) لمعالجة الرسائل
try:
    import ai_agent
    HAS_AI_AGENT = True
    logging.info("🧠 تم ربط العقل (ai_agent) بنجاح مع خدمة GYG.")
except ImportError:
    HAS_AI_AGENT = False
    logging.warning("⚠️ لم يتم العثور على ai_agent.py في نفس المسار. سيتم استخراج الرسائل فقط دون رد.")

# إعدادات تسجيل الدخول
GYG_EMAIL = "Ahmed.elkhatib@ftstravels.com"
GYG_PASSWORD = "The2007@1"
GYG_2FA_SECRET = "3RDWEZX2GAKNEN4T24DP5CV5Y7QH7OH3"
GYG_MESSAGES_URL = "https://supplier.getyourguide.com/bookings/messages"
STATE_FILE = "gyg_state.json"

# إعدادات التسجيل (دعم اللغة العربية وحفظ السجل في ملف)
log_formatter = logging.Formatter('%(asctime)s - [GYG Service] - %(message)s')

# إعداد ملف التسجيل لدعم اللغة العربية (UTF-8)
file_handler = logging.FileHandler('gyg_logs.txt', mode='a', encoding='utf-8')
file_handler.setFormatter(log_formatter)

# إعداد الكونسول (شاشة الأوامر)
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

# إعداد اللوجر الأساسي
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# مسح أي Handlers سابقة لتجنب التكرار
if logger.hasHandlers():
    logger.handlers.clear()
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def human_delay(min_seconds=1.5, max_seconds=3.5):
    """إضافة تأخير عشوائي لمحاكاة السلوك البشري"""
    time.sleep(random.uniform(min_seconds, max_seconds))

def human_type(page, selector, text):
    """الكتابة ببطء لمحاكاة الكتابة البشرية"""
    page.click(selector)
    human_delay(0.5, 1.0)
    for char in text:
        page.keyboard.press(char)
        time.sleep(random.uniform(0.05, 0.2)) # سرعة كتابة عشوائية بين الحروف
    human_delay(0.5, 1.5)

def login_to_gyg():
    max_retries = 3
    for attempt in range(max_retries):
        logging.info(f"🔄 محاولة تسجيل الدخول رقم {attempt + 1} من {max_retries}...")
        try:
            with sync_playwright() as p:
                # تشغيل المتصفح مع إعدادات لمحاكاة مستخدم حقيقي
                browser = p.chromium.launch(
                    channel="msedge",
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"] # محاولة إخفاء أن المتصفح آلي
                )
                
                # إعداد User-Agent طبيعي
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                page = context.new_page()
                
                logging.info("🌐 الانتقال إلى صفحة تسجيل الدخول...")
                # ننتظر حتى يكتمل تحميل الصفحة الأساسية
                page.goto("https://supplier.getyourguide.com/login", wait_until="domcontentloaded", timeout=60000)
                human_delay(2, 4)
                
                # 1. إدخال البريد الإلكتروني وكلمة المرور
                logging.info("🔑 إدخال بيانات الدخول ببطء...")
                
                # استخدام page.locator مع fill بدلاً من type لتجنب مشاكل المتصفح
                email_locator = page.locator('input[type="email"], input[name="email"]').first
                email_locator.wait_for(state="visible", timeout=15000)
                email_locator.click()
                human_delay(0.5, 1.5)
                email_locator.fill(GYG_EMAIL)
                
                human_delay(1, 2)
                
                password_locator = page.locator('input[type="password"], input[name="password"]').first
                password_locator.wait_for(state="visible", timeout=5000)
                password_locator.click()
                human_delay(0.5, 1.5)
                password_locator.fill(GYG_PASSWORD)
                
                # الضغط على زر تسجيل الدخول
                submit_button = page.locator('button[type="submit"]').first
                submit_button.hover()
                human_delay(0.5, 1.5)
                submit_button.click()
                
                # 2. انتظار ظهور حقل 2FA (التحقق بخطوتين)
                logging.info("⏳ انتظار صفحة التحقق بخطوتين (2FA)...")
                human_delay(3, 5) # تأخير إضافي لانتظار تحميل الصفحة التالية
                
                code_locator = page.locator('input[type="text"], input[name="code"], input[autocomplete="one-time-code"]').first
                code_locator.wait_for(state="visible", timeout=20000)
                human_delay(1, 2)
                
                # 3. توليد كود 2FA وإدخاله
                totp = pyotp.TOTP(GYG_2FA_SECRET)
                current_code = totp.now()
                logging.info(f"🛡️ تم توليد كود 2FA: {current_code}")
                
                # إدخال الكود ببطء
                code_locator.click()
                human_delay(0.5, 1.5)
                code_locator.fill(current_code)
                
                # الضغط على زر تأكيد الكود
                submit_button.hover()
                human_delay(0.5, 1.5)
                submit_button.click()
                
                # 4. التحقق من نجاح الدخول
                logging.info("✅ جاري التحقق من نجاح الدخول وانتظار تحميل الصفحة الرئيسية...")
                # الانتظار حتى يتغير الرابط إلى الصفحة الرئيسية
                page.wait_for_url("**/home**", wait_until="domcontentloaded", timeout=60000)
                
                # انتظار ظهور عنصر مميز في الصفحة الرئيسية للتأكد من اكتمال التحميل
                try:
                    page.wait_for_selector('nav a, header a', state="visible", timeout=30000)
                    logging.info("✅ تم تحميل الصفحة الرئيسية بنجاح.")
                except Exception as e:
                    logging.warning(f"⚠️ لم نتمكن من التأكد من تحميل الصفحة الرئيسية بالكامل، سنستمر: {e}")
                
                # وضع تأخير ثابت ومطول لضمان استقرار الجلسة (Session) والـ Cookies في الخلفية
                logging.info("⏳ انتظار 20 ثانية لضمان استقرار الجلسة وتحميل كافة بيانات الخلفية...")
                time.sleep(20)
                
                # التعامل مع نافذة الكوكيز إذا ظهرت
                try:
                    logging.info("🍪 التحقق من نافذة الكوكيز...")
                    # استخدام محددات أوسع للتعامل مع رسالة الكوكيز المزعجة
                    cookie_buttons = [
                        'button:has-text("I agree")',
                        'button:has-text("Accept all")',
                        'button[data-testid="cookie-banner-accept"]',
                        'button.cookie-banner__accept-button',
                        '#onetrust-accept-btn-handler',
                        '.ot-pc-refuse-all-handler'
                    ]
                    
                    # نستخدم evaluate للتأكد من إخفاء العناصر المزعجة من الـ DOM بالكامل إذا فشل الضغط
                    for selector in cookie_buttons:
                        btn = page.locator(selector).first
                        if btn.is_visible(timeout=2000):
                            btn.hover()
                            human_delay(1, 2)
                            btn.click(force=True)
                            logging.info("✅ تم قبول الكوكيز بالضغط.")
                            human_delay(2, 3)
                            break
                            
                    # إخفاء بانر الكوكيز برمجياً لتجنب تداخله مع الـ Dropdown
                    page.evaluate('''() => {
                        const cookieBanner = document.querySelector('.cookie-banner, #onetrust-banner-sdk, [data-testid="cookie-banner"]');
                        if (cookieBanner) cookieBanner.style.display = 'none';
                    }''')
                except Exception as e:
                    logging.info("لا توجد نافذة كوكيز ظاهرة.")
                    
                # محاولة إغلاق نافذة دعم الشات (Support Chat) التي تعيق الضغط
                try:
                    chat_selectors = [
                        'button[aria-label="Close chat"]',
                        'button.chat-close-btn',
                        'body > div:nth-child(1) > div > div > div > section > div:nth-child(3) > button',
                        'div[role="button"][aria-label="Minimize"]'
                    ]
                    for selector in chat_selectors:
                        chat_close_btn = page.locator(selector).first
                        if chat_close_btn.is_visible(timeout=1500):
                            chat_close_btn.click(force=True)
                            logging.info("✅ تم إغلاق نافذة دعم الشات المزعجة بالضغط.")
                            human_delay(1, 2)
                            break
                            
                    # إخفاء نافذة الشات برمجياً لتجنب تداخلها مع الـ Dropdown
                    page.evaluate('''() => {
                        const chatWidget = document.querySelector('section[class*="chat"], div[class*="chat-widget"]');
                        if (chatWidget) chatWidget.style.display = 'none';
                    }''')
                except Exception:
                    pass
    
                # التوجه مباشرة إلى صفحة الرسائل بعد تسجيل الدخول الناجح
                logging.info("📩 الانتقال إلى صفحة الرسائل...")
                
                # إخفاء العناصر المزعجة مرة أخرى قبل التفاعل مع القائمة لضمان عدم وجود تداخل (Overlap)
                try:
                    page.evaluate('''() => {
                        const chatWidget = document.querySelector('section[class*="chat"], div[class*="chat-widget"]');
                        if (chatWidget) chatWidget.style.display = 'none';
                        const cookieBanner = document.querySelector('.cookie-banner, #onetrust-banner-sdk');
                        if (cookieBanner) cookieBanner.style.display = 'none';
                    }''')
                except: pass
                
                # محاولة الوصول لصفحة الرسائل من خلال الضغط على القائمة بدلاً من الانتقال المباشر للرابط
                try:
                    # ننتظر حتى تظهر القائمة
                    page.wait_for_selector('nav, header', state="visible", timeout=15000)
                    
                    # محاولة الوصول للصفحة عن طريق النقر لتجنب اكتشاف البوت
                    bookings_nav = page.locator('nav a, header a').filter(has_text="Bookings").first
                    if bookings_nav.is_visible(timeout=5000):
                        bookings_nav.click()
                        human_delay(1, 2)
                        messages_link = page.locator('a[href*="/messages"]').first
                        if messages_link.is_visible(timeout=5000):
                            messages_link.click()
                        else:
                            page.goto(GYG_MESSAGES_URL, wait_until="domcontentloaded", timeout=60000)
                    else:
                        page.goto(GYG_MESSAGES_URL, wait_until="domcontentloaded", timeout=60000)
                except Exception as e:
                    logging.info(f"التحويل عبر القائمة فشل، استخدام الرابط المباشر: {e}")
                    page.goto(GYG_MESSAGES_URL, wait_until="domcontentloaded", timeout=60000)
                
                # الانتظار حتى يظهر عنوان الرسائل أو صندوق البحث
                # أضفنا التحقق من وجود رسالة خطأ الجلسة للتعامل معها بسرعة
                try:
                    # ننتظر ظهور صندوق البحث أو رسالة الخطأ أيهما يظهر أولاً
                    page.wait_for_selector('h1:has-text("Messages"), input[placeholder="Search"], :text("There was an error with your session")', state="visible", timeout=30000)
                    
                    # التحقق إذا كانت رسالة الخطأ موجودة في الصفحة
                    error_msg = page.locator(':text("There was an error with your session")').first
                    if error_msg.is_visible(timeout=2000):
                        raise Exception("الموقع يطلب تسجيل الدخول مرة أخرى (Session Error).")
                        
                except Exception as wait_e:
                    if "Session Error" in str(wait_e):
                        raise wait_e
                    else:
                        logging.warning(f"⚠️ تأخر تحميل صفحة الرسائل: {wait_e}")
                        
                human_delay(2, 4)
                
                # التحقق النهائي من الرابط قبل المتابعة
                if "login" in page.url or "auth" in page.url:
                    raise Exception("تم تحويلنا إلى صفحة تسجيل الدخول مرة أخرى.")
                
                logging.info("🎉 تم الوصول لصفحة الرسائل بنجاح!")
                
                # الضغط على تبويب Unread
                logging.info("📨 جاري البحث عن تبويب Unread والضغط عليه...")
                
                # تنظيف الشاشة من أي نوافذ منبثقة قبل محاولة النقر
                try:
                    page.evaluate('''() => {
                        const chatWidget = document.querySelector('section[class*="chat"], div[class*="chat-widget"]');
                        if (chatWidget) chatWidget.style.display = 'none';
                        const cookieBanner = document.querySelector('.cookie-banner, #onetrust-banner-sdk');
                        if (cookieBanner) cookieBanner.style.display = 'none';
                    }''')
                except: pass
                
                # استخدام أكثر من محدد (Selector) لضمان العثور على الزر بناءً على الـ HTML المرفق
                unread_tab = page.locator('button:has-text("Unread"), button[data-testid="inbox-filter-unread"]').first
                
                # ننتظر حتى يكون الزر قابلاً للضغط
                unread_tab.wait_for(state="visible", timeout=10000)
                
                # تحريك الماوس للزر بشكل طبيعي ثم الضغط
                unread_tab.hover()
                human_delay(1, 2)
                unread_tab.click()
                logging.info("✅ تم الضغط على تبويب Unread بنجاح!")
                
                # الانتظار لتحميل البيانات
                human_delay(3, 5)
                
                # التأكد من بقاءنا في صفحة الرسائل وعدم التوجيه لصفحة الخطأ/تسجيل الخروج
                if "login" in page.url:
                    raise Exception("تم تسجيل الخروج بشكل غير متوقع بعد الضغط على التبويب.")
                    
                # حفظ الجلسة قبل إغلاق المتصفح (مهم جداً للحفاظ على الجلسة حية)
                context.storage_state(path=STATE_FILE)
                logging.info("💾 تم حفظ الجلسة (Session) بنجاح.")
                
                # استخراج الرسائل غير المقروءة بعد الضغط على التبويب
                messages = extract_unread_messages(page)
                
                # بقاء المتصفح مفتوحاً لثواني للتأكد من الشاشة قبل الإغلاق
                time.sleep(5)
                # إعادة حفظ الجلسة مرة أخيرة قبل الإغلاق لضمان أحدث الكوكيز
                context.storage_state(path=STATE_FILE)
                
                browser.close()
                return messages # نجحنا، نخرج من الحلقة
                
        except Exception as e:
            if "SESSION_EXPIRED" in str(e):
                logging.warning("⚠️ الجلسة انتهت أثناء المعالجة، سيتم إعادة تسجيل الدخول فوراً...")
                if os.path.exists(STATE_FILE):
                    os.remove(STATE_FILE)
                # لا ننتظر كثيراً، ننتقل للمحاولة التالية (التي ستسجل الدخول من الصفر)
                try: browser.close()
                except: pass
                continue
                
            logging.error(f"❌ حدث خطأ في المحاولة {attempt + 1}: {e}")
            try:
                page.screenshot(path=f"gyg_error_attempt_{attempt+1}.png")
                logging.info(f"📸 تم أخذ صورة للخطأ باسم gyg_error_attempt_{attempt+1}.png")
            except:
                pass
            
            try:
                browser.close()
            except:
                pass
                
            if attempt < max_retries - 1:
                logging.info("⏳ الانتظار 10 ثواني قبل المحاولة التالية...")
                time.sleep(10)
            else:
                logging.error("❌ فشلت جميع المحاولات للوصول إلى رسائل GYG.")
                return []

def get_existing_reply_from_airtable(booking_ref, latest_message):
    """
    يبحث في Airtable عن الحجز، ويتحقق مما إذا كانت آخر رسالة للعميل
    موجودة في AI Chat Log، وإذا كانت كذلك، يقوم بجلب الرد الذي تم إرساله عبر الإيميل.
    """
    try:
        import re
        from ai_agent import airtable_service
        if not airtable_service:
            return None, False
            
        # البحث عن الحجز باستخدام رقم الحجز مباشرة
        # قمنا بتحسين البحث ليتعامل مع الفراغات وأي أحرف غير مرئية
        booking_ref_clean = str(booking_ref).strip()
        
        # تعطيل طباعة التحذيرات المزعجة أثناء البحث
        import logging
        old_level = logging.getLogger().getEffectiveLevel()
        logging.getLogger().setLevel(logging.ERROR)
        
        try:
            found_record = airtable_service.find_booking_by_number(booking_ref_clean)
            
            # إذا لم يجده بالطريقة المباشرة، نحاول البحث الشامل (القديم)
            if not found_record:
                all_bookings = airtable_service.get_all_bookings(max_records=100)
                for b in all_bookings:
                    if booking_ref_clean and booking_ref_clean in str(b.get('fields', {}).get('Booking Nr.', '')):
                        found_record = b
                        break
        finally:
            # استعادة مستوى اللوج الطبيعي
            logging.getLogger().setLevel(old_level)
                
        if not found_record:
            logging.info(f"⚠️ لم يتم العثور على الحجز {booking_ref} في Airtable.")
            return None, False
            
        chat_log = found_record['fields'].get('AI Chat Log') or found_record['fields'].get('AI Chat log', '')
        if not chat_log:
            logging.info("⚠️ لا يوجد سجل محادثة (AI Chat Log) لهذا الحجز.")
            return None, False
            
        # نأخذ جزء من رسالة العميل لتجنب مشاكل المسافات وتنسيق النصوص
        # نستخدم جزء من الرسالة وتجاهل الفواصل والأسطر الجديدة
        clean_latest = re.sub(r'\s+', '', latest_message.strip()[:50].lower())
        clean_chat_log = re.sub(r'\s+', '', chat_log.lower())
        
        # البحث في السجل المنظف
        # قمنا بتحسين البحث في السجل حيث أنه أحياناً يتم تسجيل الرد بأسماء مختلفة أو قد تكون الرسالة مقتطعة قليلاً
        if clean_latest in clean_chat_log or clean_latest[:20] in clean_chat_log:
            logging.info("✅ تم العثور على رسالة العميل في Airtable، جاري استخراج الرد...")
            
            # البحث عن آخر رد من النظام أو الموظف في السجل الأصلي (غير المنظف)
            # تم تحديث الـ Regex ليتناسب مع شكل السجل المرفق
            matches = re.findall(r'\[(AI_Learning - System|AI Assistant|Human Agent)\]:\s*(.*?)(?=\n\n\[\d{4}-\d{2}-\d{2}|\Z)', chat_log, re.DOTALL)
            if matches:
                last_reply = matches[-1][1].strip()
                # تنظيف الرد من أي علامات مسودة
                last_reply = last_reply.replace('[PROPOSED_DRAFT]', '').strip()
                return last_reply, True # True means it was found in Airtable
            else:
                logging.info("⚠️ لم يتم العثور على رد الذكاء الاصطناعي في السجل. جاري البحث عن أي رد...")
                # محاولة بحث بديلة إذا كان التنسيق مختلف قليلاً
                alt_matches = re.findall(r'\[.*?\]\s*\[(.*?)\]:\s*(.*?)(?=\n\n\[|$)', chat_log, re.DOTALL)
                for sender, reply in reversed(alt_matches):
                    if "user" not in sender.lower() and "customer" not in sender.lower():
                        clean_reply = reply.replace('[PROPOSED_DRAFT]', '').strip()
                        if clean_reply:
                            return clean_reply, True
                
                logging.info("⚠️ لم نتمكن من استخراج أي رد صالح.")
                return None, False
        else:
            logging.info("⚠️ رسالة العميل الأخيرة غير موجودة في سجل Airtable، مما يعني أنه لم يتم الرد عليها عبر الإيميل بعد.")
            return None, False
            
    except Exception as e:
        logging.error(f"❌ خطأ أثناء البحث في Airtable: {e}")
        
    return None, False

def extract_unread_messages(page):
    """دالة لاستخراج الرسائل من قائمة Unread مع محاولة التحديث في حال عدم ظهورها"""
    logging.info("🔍 جاري قراءة الرسائل غير المقروءة...")
    
    max_refresh_attempts = 5
    found_messages = False
    
    # استخدام محدد أكثر مرونة وموثوقية يعتمد على data-testid لتجنب مشاكل تغير الكلاسات
    # تم دمج المحدد الدقيق مع المحدد الأقوى لضمان العثور على الرسالة
    exact_first_message_selector = 'div[data-testid="inbox-conversation-item"]'
    
    # انتظار قصير إضافي بعد الضغط على التبويب للسماح للرسائل بالظهور
    human_delay(2, 3)
    
    for attempt in range(max_refresh_attempts):
        try:
            # ننتظر حتى تظهر قائمة الرسائل
            page.wait_for_selector('.messages-container', timeout=10000)
            
            first_message_locator = page.locator(exact_first_message_selector).first
            
            if first_message_locator.is_visible(timeout=5000):
                logging.info(f"📬 تم العثور على رسالة غير مقروءة في المحاولة {attempt + 1}.")
                found_messages = True
                break # وجدنا الرسائل، نتوقف عن التحديث ونخرج من الحلقة
            else:
                logging.warning(f"📭 لم يتم العثور على رسائل في المحاولة {attempt + 1}. جاري تحديث الصفحة...")
                try:
                    # تحديث الصفحة بشكل كامل لضمان جلب البيانات
                    page.reload(wait_until="domcontentloaded", timeout=30000)
                    human_delay(3, 5)
                    
                    # إعادة الضغط على تبويب Unread بعد التحديث
                    unread_tab = page.locator('button:has-text("Unread"), button[data-testid="inbox-filter-unread"]').first
                    if unread_tab.is_visible(timeout=5000):
                        unread_tab.click()
                        human_delay(3, 5)
                except Exception as reload_err:
                    logging.warning(f"⚠️ فشل تحديث الصفحة: {reload_err}")
                    
        except Exception as e:
            logging.warning(f"⚠️ خطأ أثناء البحث عن الرسائل في المحاولة {attempt + 1}: {e}")
            if attempt < max_refresh_attempts - 1:
                logging.info("جاري تحديث الصفحة والمحاولة مرة أخرى...")
                try:
                    page.reload(wait_until="domcontentloaded", timeout=30000)
                    human_delay(3, 5)
                    
                    unread_tab = page.locator('button:has-text("Unread"), button[data-testid="inbox-filter-unread"]').first
                    if unread_tab.is_visible(timeout=5000):
                        unread_tab.click()
                        human_delay(3, 5)
                except Exception as inner_e:
                    logging.error(f"❌ حدث خطأ قاتل أثناء محاولة التحديث: {inner_e}")
                    # خروج من الحلقة إذا تم إغلاق المتصفح لتجنب التكرار اللانهائي للأخطاء
                    if "closed" in str(inner_e).lower():
                        break
                
    if not found_messages:
        logging.info("📭 لا توجد رسائل غير مقروءة حالياً بعد جميع المحاولات.")
        return []
        
    unread_conversations = []
    processed_bookings = set()
    max_messages_to_process = 10
    processed_count = 0
    
    while processed_count < max_messages_to_process:
        try:
            # التحقق السريع من حالة الجلسة قبل كل محادثة
            if "login" in page.url or "auth" in page.url:
                logging.error("❌ تم اكتشاف صفحة تسجيل الدخول. الجلسة انتهت.")
                raise Exception("SESSION_EXPIRED")
                
            error_msg = page.locator(':text("There was an error with your session")').first
            if error_msg.is_visible(timeout=1000):
                logging.error("❌ تم اكتشاف رسالة خطأ الجلسة.")
                raise Exception("SESSION_EXPIRED")
            # انتظار ظهور الحاوية
            page.wait_for_selector('.messages-container', timeout=10000)
            
            # جلب كل الرسائل غير المقروءة الظاهرة
            message_elements = page.locator(exact_first_message_selector).all()
            
            if not message_elements:
                logging.info("🎉 لا توجد رسائل غير مقروءة إضافية.")
                break
                
            # العثور على أول رسالة لم يتم معالجتها بعد
            target_element = None
            for el in message_elements:
                try:
                    # محاولة استخراج المعرف أو النص للتحقق من عدم التكرار
                    ref = el.get_attribute("data-booking-reference", timeout=1000)
                    if ref and ref != "Unknown_Booking" and ref in processed_bookings:
                        continue
                        
                    el_text = el.inner_text()
                    # إذا كان اسم العميل أو رقم الحجز موجوداً في قائمة المعالجة نتجاوزه
                    if any(pb in el_text for pb in processed_bookings if pb and pb != "Unknown_Booking" and len(pb) > 3):
                        continue
                except:
                    pass
                
                target_element = el
                break
                
            if not target_element:
                logging.info("✅ تم معالجة جميع الرسائل غير المقروءة الظاهرة.")
                break
                
            logging.info(f"🔄 جاري فتح المحادثة رقم {processed_count + 1}...")
            target_element.scroll_into_view_if_needed()
            target_element.hover()
            human_delay(1, 2)
            target_element.click()
            
            logging.info("⏳ انتظار تحميل محتوى المحادثة...")
            human_delay(4, 6) 
            
            # استخراج اسم العميل ورقم الحجز
            header_locator = page.locator('h3.chat-header__name, div.chat-header__name').first
            customer_name = header_locator.inner_text(timeout=10000) if header_locator.is_visible(timeout=5000) else "GYG_Customer"
            
            booking_ref = "Unknown_Booking"
            try:
                booking_ref_attr = target_element.get_attribute("data-booking-reference", timeout=2000)
                if booking_ref_attr:
                    booking_ref = booking_ref_attr
                else:
                    exact_meta_locator = page.locator('#__nuxt > div > div > main > div.max-w-\\[100vw\\].px-4.md\\:px-6.pb-20 > div > div.messages-container > div:nth-child(2) > div > div > div.sticky.top-0.z-1.bg-surface-primary.md\\:rounded-t-xl > div > div > div.chat-header__info > div > span:nth-child(2)')
                    if exact_meta_locator.is_visible(timeout=3000):
                        booking_text = exact_meta_locator.inner_text()
                        import re
                        match = re.search(r'(GYG\w+)', booking_text)
                        if match:
                            booking_ref = match.group(1)
                    else:
                        meta_locator = page.locator('.chat-header__meta span:has(.i-tickets) ~ span, .chat-header__meta span:has-text("GYG")').first
                        if meta_locator.is_visible(timeout=3000):
                            booking_text = meta_locator.inner_text()
                            import re
                            match = re.search(r'(GYG\w+)', booking_text)
                            if match:
                                booking_ref = match.group(1)
            except Exception:
                pass
                
            # إضافة الحجز للقائمة حتى لا نعالجه مرة أخرى
            if booking_ref != "Unknown_Booking":
                processed_bookings.add(booking_ref)
            if customer_name and customer_name != "GYG_Customer":
                processed_bookings.add(customer_name.strip())
                
            user_id = f"{customer_name.strip()} ({booking_ref})"
            
            human_delay(2, 3)
            
            chat_box_locator = '#__nuxt > div > div > main > div.max-w-\\[100vw\\].px-4.md\\:px-6.pb-20 > div > div.messages-container > div:nth-child(2) > div > div > div.md\\:border-t-2.md\\:border-t-surface-secondary > div.overflow-y-scroll.p-4.md\\:h-full'
            
            try:
                messages_texts = page.locator(f'{chat_box_locator} div.break-words').all_inner_texts()
            except:
                messages_texts = []
                
            if not messages_texts:
                 messages_texts = page.locator('div[data-testid="inbox-message-list"] div[data-testid="message-bubble-traveler"] div.break-words').all_inner_texts()
                 
            if not messages_texts:
                 messages_texts = page.locator('div.bg-surface-secondary.text-label-primary.break-words').all_inner_texts()
                 
            if messages_texts:
                valid_messages = [msg for msg in messages_texts if msg.strip()]
                if valid_messages:
                    full_chat_context = "\n".join(valid_messages)
                    latest_message = valid_messages[-1]
                    
                    logging.info(f"👤 العميل: {user_id}")
                    logging.info(f"💬 آخر رسالة: {latest_message.strip()[:50]}...")
                    logging.info(f"📚 تم سحب {len(valid_messages)} رسالة لتكوين السياق للعقل.")
                    
                    if HAS_AI_AGENT:
                        logging.info("🤖 جاري فحص ما إذا تم الرد على هذه الرسالة مسبقاً في Airtable عبر الإيميل...")
                        ai_response, found_in_airtable = get_existing_reply_from_airtable(booking_ref, latest_message)
                        
                        if found_in_airtable and ai_response:
                            logging.info(f"✅ تم العثور على رد سابق في Airtable: {ai_response.strip()[:100]}...")
                        else:
                            logging.info("🤖 لم يتم العثور على رد سابق، جاري إرسال سياق المحادثة لعقل الذكاء الاصطناعي لتوليد رد جديد...")
                            ai_response, _ = ai_agent.process_core_logic(f"GYG_{user_id}", full_chat_context)
                            logging.info(f"✅ رد العقل المقترح الجديد: {ai_response.strip()[:100]}...")
                            
                        if ai_response:
                            logging.info("✍️ جاري كتابة الرد في صندوق المحادثة...")
                            
                            reply_box_selector = '#__nuxt > div > div > main > div.max-w-\\[100vw\\].px-4.md\\:px-6.pb-20 > div > div.messages-container > div:nth-child(2) > div > div > div.md\\:border-t-2.md\\:border-t-surface-secondary > div.md\\:absolute.md\\:bottom-0.px-2.pb-3.w-full > div > div > div > div.p-editor-content.border-none.ql-container.ql-snow > div.ql-editor'
                            reply_box = page.locator(reply_box_selector).first
                            
                            if not reply_box.is_visible(timeout=3000):
                                reply_box = page.locator('.ql-editor, div[contenteditable="true"]').first
                            
                            if reply_box.is_visible(timeout=5000):
                                reply_box.click()
                                human_delay(1, 2)
                                
                                page.evaluate('(args) => { const [element, text] = args; element.innerHTML = `<p>${text}</p>`; }', [reply_box.element_handle(), ai_response.replace('\n', '<br>')])
                                reply_box.type(" ")
                                human_delay(1, 2)
                                
                                send_button_selector = '#__nuxt > div > div > main > div.max-w-\\[100vw\\].px-4.md\\:px-6.pb-20 > div > div.messages-container > div:nth-child(2) > div > div > div.md\\:border-t-2.md\\:border-t-surface-secondary > div.md\\:absolute.md\\:bottom-0.px-2.pb-3.w-full > div > div > div > div.p-editor-toolbar.ql-toolbar.ql-snow > div > div.w-8.h-8.rounded-full.flex.items-center.justify-center.bg-interactive-primary.cursor-pointer.hover\\:bg-interactive-primary-hovered'
                                send_button = page.locator(send_button_selector).first
                                
                                if not send_button.is_visible(timeout=3000):
                                    send_button = page.locator('div.p-editor-toolbar div.bg-interactive-primary.cursor-pointer').first
                                    
                                if send_button.is_visible(timeout=3000):
                                    send_button.hover(force=True)
                                    human_delay(1, 2)
                                    send_button.click(force=True)
                                    logging.info("🚀 تم إرسال الرد للعميل بنجاح!")
                                    human_delay(3, 5)
                                else:
                                    logging.warning("⚠️ لم نتمكن من العثور على زر الإرسال.")
                            else:
                                logging.warning("⚠️ صندوق الكتابة غير متاح في هذه المحادثة (قد تكون مغلقة).")
                        else:
                            logging.warning("⚠️ لا يوجد رد متاح للإرسال.")
                            
                    unread_conversations.append({
                        "user_id": user_id,
                        "full_context": full_chat_context,
                        "ai_reply": ai_response if HAS_AI_AGENT else None
                    })
                else:
                    logging.info(f"⚠️ المحادثة لا تحتوي على نصوص واضحة.")
            else:
                 logging.info(f"⚠️ لم نتمكن من استخراج رسائل للمحادثة.")
                 
            processed_count += 1
            logging.info("⏳ انتظار 5 ثواني قبل الانتقال للمحادثة التالية...")
            time.sleep(5)
            
            # العودة للرسائل غير المقروءة لضمان تحديث القائمة إذا لزم الأمر
            try:
                unread_tab = page.locator('button:has-text("Unread"), button[data-testid="inbox-filter-unread"]').first
                if unread_tab.is_visible(timeout=3000):
                    unread_tab.click()
                    human_delay(2, 3)
                    
                # إعادة تحميل الصفحة كخيار بديل قوي لضمان جلب القائمة الجديدة وتحديث الـ DOM
                # هذا يحل مشكلة الرسائل المخفية أو تكرار نفس الرسالة
                page.reload(wait_until="domcontentloaded", timeout=30000)
                human_delay(3, 5)
                
                # الضغط على تبويب Unread مرة أخرى بعد التحديث
                unread_tab = page.locator('button:has-text("Unread"), button[data-testid="inbox-filter-unread"]').first
                if unread_tab.is_visible(timeout=5000):
                    unread_tab.click()
                    human_delay(2, 3)
            except Exception as e:
                logging.warning(f"⚠️ فشل تحديث قائمة الرسائل: {e}")
                 
        except Exception as e:
            if "SESSION_EXPIRED" in str(e):
                logging.warning("⚠️ الجلسة انتهت أثناء المعالجة، سيتم إيقاف الدورة ليتم إعادة تسجيل الدخول.")
                raise Exception("SESSION_EXPIRED") # رفع الخطأ للدالة الرئيسية لتعيد تسجيل الدخول
                
            logging.warning(f"⚠️ فشل في معالجة المحادثة: {e}")
            break # الخروج من الحلقة في حال حدوث خطأ كبير لتجنب التعليق
            
    return unread_conversations

def run_gyg_agent():
    """دالة التشغيل الرئيسية التي تعتمد على الجلسة المحفوظة وتدعم إعادة التشغيل اللانهائي"""
    while True: # حلقة لا نهائية لضمان استمرارية العمل وإعادة المحاولة في حال طرد الجلسة
        need_relogin = False
        messages = []
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(channel="msedge", headless=False, args=["--disable-blink-features=AutomationControlled"])
                
                # إذا كان ملف الجلسة موجوداً، نستخدمه لتخطي تسجيل الدخول
                if os.path.exists(STATE_FILE):
                    logging.info("🔄 استخدام الجلسة المحفوظة لتسريع الدخول...")
                    context = browser.new_context(
                        storage_state=STATE_FILE,
                        viewport={'width': 1280, 'height': 800},
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    )
                    page = context.new_page()
                    
                    try:
                        # نستخدم wait_until='domcontentloaded' لتقليل احتمالية الـ Timeout
                        page.goto(GYG_MESSAGES_URL, wait_until="domcontentloaded", timeout=60000)
                        
                        # نتحقق مما إذا كان الموقع قد حولنا لصفحة تسجيل الدخول مرة أخرى (الجلسة منتهية)
                        current_url = page.url
                        if "login" in current_url:
                            raise Exception("SESSION_EXPIRED")
                            
                        page.wait_for_selector('h1:has-text("Messages"), input[placeholder="Search"]', timeout=15000)
                        
                        # الضغط على Unread
                        unread_tab = page.locator('button:has-text("Unread"), button[data-testid="inbox-filter-unread"]').first
                        unread_tab.click()
                        human_delay(3, 5)
                        
                        if "login" in page.url:
                            raise Exception("SESSION_EXPIRED")
                        
                        # استخراج الرسائل
                        messages = extract_unread_messages(page)
                        
                        # إذا وصلنا هنا بنجاح، نكسر الحلقة اللانهائية وننهي السكربت أو نتركه ينتظر دورة قادمة
                        logging.info("✅ انتهت دورة فحص الرسائل بنجاح. سيتم إيقاف السكربت حتى الدورة القادمة.")
                        break
                        
                    except Exception as e:
                        if "SESSION_EXPIRED" in str(e):
                            logging.error("⚠️ الجلسة منتهية الصلاحية. سيتم تسجيل الدخول من جديد...")
                        else:
                            logging.error(f"⚠️ فشل استخدام الجلسة المحفوظة أو انتهت أثناء العمل: {e}")
                            
                        logging.info("سأقوم بحذف الجلسة لتسجيل الدخول من جديد...")
                        if os.path.exists(STATE_FILE):
                            os.remove(STATE_FILE)
                        need_relogin = True
                else:
                    logging.info("🆕 لا توجد جلسة محفوظة، يجب تسجيل الدخول...")
                    need_relogin = True
                    
                browser.close()
                
            # استدعاء دالة تسجيل الدخول خارج الـ context manager الأول لمنع تداخل الجلسات
            if need_relogin:
                logging.info("بدء عملية تسجيل الدخول من الصفر...")
                messages = login_to_gyg()
                # بعد تسجيل الدخول ومعالجة الرسائل بنجاح نكسر الحلقة
                break
                
        except Exception as global_e:
            logging.error(f"💥 خطأ عام في النظام، جاري إعادة المحاولة: {global_e}")
            time.sleep(10)
            
    return messages

if __name__ == "__main__":
    # بدلاً من login_to_gyg() مباشرة، نستخدم دالة التشغيل الذكية
    run_gyg_agent()
