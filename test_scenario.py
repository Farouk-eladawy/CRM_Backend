import json
import logging
from pyairtable.formulas import match
from ai_agent import AIAgent

# إعداد تسجيل بسيط للاختبار
logging.basicConfig(level=logging.INFO)

def live_test_customer_inquiry():
    print("🚀 بدء اختبار النظام (Live Test) مع بيانات حقيقية...")
    
    agent = AIAgent()
    
    # بيانات العميل
    customer_message = "انا عاوز استفسر عن ميعاد الالتقاط وعاوزك ترد عليا وده رقم الحجز الخاص بيا BR-test1532135"
    booking_ref = "BR-test1532135" # القيمة التي سنبحث عنها
    
    print(f"\n📩 رسالة العميل: {customer_message}")
    print(f"� جاري البحث في Airtable عن الحجز رقم: {booking_ref}...")
    
    # 1. البحث في Airtable
    # سنبحث في حقل "Product ID" كما هو مستخدم في السكربتات السابقة
    try:
        # formula = match({"Product ID": booking_ref})
        # records = agent.table.all(formula=formula)
        
        # استخدام اسم الحقل الصحيح من ملف TableFields.csv
        # الحقل هو "Booking Nr."
        formula = f"{{Booking Nr.}} = '{booking_ref}'"
        records = agent.table.all(formula=formula)
        
    except Exception as e:
        print(f"❌ خطأ أثناء البحث في Airtable: {e}")
        records = []

    pickup_time = None
    pickup_status = "Not Found"
    
    if records:
        record = records[0]
        fields = record['fields']
        print(f"✅ تم العثور على الحجز! (ID: {record['id']})")
        
        # محاولة العثور على حقل ميعاد الالتقاط
        # سنبحث عن حقول تحتوي على كلمة Pickup أو Time
        # بناءً على config.json الحقل المهم هو: "Whatsapp Pickup Time2"
        target_field = agent.config['airtable']['fields']['update_status']
        
        if target_field in fields:
            pickup_time = fields[target_field]
            pickup_status = f"Available: {pickup_time}"
            print(f"📅 ميعاد الالتقاط الموجود: {pickup_time}")
        else:
            # نحاول البحث عن أي حقل آخر يحتوي على وقت
            possible_fields = [k for k in fields.keys() if 'pickup' in k.lower() or 'time' in k.lower()]
            if possible_fields:
                print(f"⚠️ الحقل المحدد ({target_field}) غير موجود، لكن وجدت حقول مشابهة: {possible_fields}")
                # نأخذ أول واحد كاحتياط
                pickup_time = fields[possible_fields[0]]
                pickup_status = f"Available (Alternative Field): {pickup_time}"
            else:
                pickup_status = "Not Set Yet"
                print("❌ لم يتم العثور على أي ميعاد التقاط في السجل.")
    else:
        print("❌ لم يتم العثور على أي سجل بهذا الرقم.")

    # 2. بناء الـ Prompt بناءً على النتيجة الحقيقية
    
    # رسالة الاعتذار من الكونفيج
    try:
        no_pickup_msg = agent.config.get('MESSAGES', {}).get('NO_PICKUP_INFO', {}).get('ar', "نعتذر، الموعد غير محدد بعد.")
    except:
        no_pickup_msg = "نعتذر، الموعد غير محدد بعد."

    if pickup_time:
        db_status = f"Pickup time is CONFIRMED: {pickup_time}"
        instruction = f"Inform the customer that their pickup time is: {pickup_time}. Wish them a pleasant trip."
    else:
        db_status = "Pickup time NOT set yet."
        instruction = f"Apologize politely using this phrase: '{no_pickup_msg}'"

    final_prompt = f"""
    Customer Message: "{customer_message}"
    Context: Customer asking about pickup time for booking {booking_ref}.
    Real Database Findings: {db_status}
    
    Instructions:
    1. Acknowledge the booking ({booking_ref}).
    2. {instruction}
    3. Be professional and helpful in Arabic.
    """
    
    print("\n🤖 جاري استدعاء DeepSeek AI لتوليد الرد...")
    response = agent.query_ai(final_prompt)
    
    print("\n" + "="*50)
    print("🗣️ رد النظام (AI Response):")
    print("="*50)
    print(response)
    print("="*50)

if __name__ == "__main__":
    live_test_customer_inquiry()
