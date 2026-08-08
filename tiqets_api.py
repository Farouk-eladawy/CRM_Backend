import os
import uuid
import datetime
from flask import Flask, request, jsonify, abort
from pyairtable import Api
from pyairtable.formulas import match

app = Flask(__name__)

# ==========================================
# ⚙️ الإعدادات (Configuration)
# ==========================================
# ضع مفتاح Airtable الخاص بك هنا
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY", "YOUR_AIRTABLE_API_KEY")
# ضع Base ID الخاص بقاعدة بياناتك هنا
AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID", "YOUR_AIRTABLE_BASE_ID")

# Base ID الخاص بجدول التذاكر الجديد (لأنه تم نقله)
TICKETS_BASE_ID = os.environ.get("TICKETS_BASE_ID", "appZLYzQcuH4MDHCI")

# مفتاح الحماية الخاص بـ Tiqets (تشاركه معهم)
# مفتاح احترافي عشوائي تم إنشاؤه لضمان الأمان
TIQETS_API_KEY = os.environ.get("TIQETS_API_KEY", "fts_tq_9xK2mP4vL8nR5jW3cQ7hY1bN6dM0sF")

# أسماء الجداول الثابتة
PRODUCTS_CATALOG_TABLE = "Products_Catalog"
LIST_TABLE = "List"

# تهيئة الاتصال بـ Airtable
api = Api(AIRTABLE_API_KEY)
catalog_table = api.table(AIRTABLE_BASE_ID, PRODUCTS_CATALOG_TABLE)
list_table = api.table(AIRTABLE_BASE_ID, LIST_TABLE)

# ==========================================
# 🔒 التحقق من المصادقة (Authentication)
# ==========================================
@app.before_request
def verify_api_key():
    # استثناء مسار فحص الصحة (Health check)
    if request.path == "/health":
        return
        
    api_key = request.headers.get("API-Key")
    if not api_key or api_key != TIQETS_API_KEY:
        abort(403, description="Forbidden - Missing or incorrect API key")

# ==========================================
# 🛠️ 1. كتالوج المنتجات (Product Catalog)
# ==========================================
@app.route('/v2/products', methods=['GET'])
def get_products():
    try:
        # جلب جميع الرحلات المفعلة من الكتالوج
        records = catalog_table.all(formula="Active=1")
        products = []
        
        for record in records:
            fields = record.get("fields", {})
            product = {
                "id": fields.get("Product ID", ""),
                "name": fields.get("Product Name", ""),
                "description": fields.get("Description", ""),
                "use_timeslots": fields.get("Use Timeslots", False),
                "is_refundable": fields.get("Is Refundable", False),
                "provides_pricing": fields.get("Provides Pricing", False),
                "cutoff_time": fields.get("Cutoff Time", 0)
            }
            
            # إضافة الحقول الاختيارية إن وجدت
            if "Max Tickets" in fields:
                product["max_tickets_per_order"] = fields["Max Tickets"]
            if "Required Order Data" in fields:
                product["required_order_data"] = fields["Required Order Data"]
            if "Required Visitor Data" in fields:
                product["required_visitor_data"] = fields["Required Visitor Data"]
                
            products.append(product)
            
        return jsonify(products), 200
        
    except Exception as e:
        print(f"Error in get_products: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# ==========================================
# 📅 2. التوافر (Availability)
# ==========================================
@app.route('/v2/products/<product_id>/availability', methods=['GET'])
def get_availability(product_id):
    try:
        start_date = request.args.get('start')
        end_date = request.args.get('end')
        
        if not start_date or not end_date:
            return jsonify({"error_code": 1000, "error": "Missing argument", "message": "Required argument start or end was not found"}), 400

        # 1. البحث عن الرحلة في الكتالوج
        product_records = catalog_table.all(formula=match({"Product ID": product_id}))
        if not product_records:
            return jsonify({"error_code": 1001, "error": "Missing product", "message": f"Product with ID {product_id} doesn't exist"}), 400
            
        product_fields = product_records[0]["fields"]
        daily_capacity = product_fields.get("Daily Capacity", 0)
        provides_pricing = product_fields.get("Provides Pricing", False)
        currency = product_fields.get("Currency", "USD")
        adult_price = str(product_fields.get("Adult Price", "0"))
        child_price = str(product_fields.get("Child Price", "0"))
        product_name = product_fields.get("Product Name", "")
        use_timeslots = product_fields.get("Use Timeslots", False)
        
        # تحويل التواريخ
        start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        
        availability_response = {}
        
        # نمر على كل يوم في النطاق المطلوب
        delta = datetime.timedelta(days=1)
        current_dt = start_dt
        
        while current_dt <= end_dt:
            date_str = current_dt.strftime("%Y-%m-%d")
            
            # 2. حساب الحجوزات الحالية لهذا اليوم من جدول List
            # نبحث عن الحجوزات التي تتطابق في التاريخ واسم الرحلة
            formula = f"AND({{Date Trip}}='{date_str}', FIND('{product_name}', {{trip Name}}))"
            existing_bookings = list_table.all(formula=formula)
            
            total_booked = 0
            for booking in existing_bookings:
                total_booked += booking["fields"].get("Total Travelers", 0)
                
            available_tickets = max(0, daily_capacity - total_booked)
            
            # تجهيز Variants (البالغ والطفل)
            variants = []
            if available_tickets > 0:
                adult_variant = {
                    "id": "ADT",
                    "name": "Adult",
                    "available_tickets": available_tickets
                }
                child_variant = {
                    "id": "CHD",
                    "name": "Child",
                    "available_tickets": available_tickets
                }
                
                if provides_pricing:
                    adult_variant["price"] = {"amount": adult_price, "currency": currency}
                    child_variant["price"] = {"amount": child_price, "currency": currency}
                    
                variants = [adult_variant, child_variant]
            
            # تحديد الوقت (Timeslot أو 00:00)
            time_str = "00:00" if not use_timeslots else "10:00" # افتراضياً 10 صباحاً كمثال
            datetime_key = f"{date_str}T{time_str}"
            
            availability_response[datetime_key] = {
                "available_tickets": available_tickets,
                "variants": variants
            }
            
            current_dt += delta
            
        return jsonify(availability_response), 200

    except Exception as e:
        print(f"Error in get_availability: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# ==========================================
# 🛑 3. الحجز المبدئي (Reservation)
# ==========================================
@app.route('/v2/products/<product_id>/reservation', methods=['POST'])
def make_reservation(product_id):
    try:
        data = request.json
        
        # التحقق من المنتج
        product_records = catalog_table.all(formula=match({"Product ID": product_id}))
        if not product_records:
            return jsonify({"error_code": 1001, "error": "Missing product", "message": f"Product with ID {product_id} doesn't exist"}), 400
            
        product_fields = product_records[0]["fields"]
        product_name = product_fields.get("Product Name", "")
        
        # استخراج بيانات العميل والتذاكر
        customer = data.get("customer", {})
        tickets = data.get("tickets", [])
        
        # Provide a default datetime if not provided or extract correctly
        datetime_val = data.get("datetime", "") # مثلا 2022-12-26T15:30
        
        if datetime_val:
            date_trip = datetime_val.split("T")[0]
        else:
            # Fallback to today's date if no datetime is provided by Tiqets
            date_trip = datetime.datetime.today().strftime("%Y-%m-%d")
        
        total_quantity = sum(t.get("quantity", 0) for t in tickets)
        full_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
        
        # توليد ID حجز مبدئي
        reservation_id = f"RES-{uuid.uuid4().hex[:8].upper()}"
        
        # إنشاء السجل في جدول List كحجز مبدئي
        new_booking = list_table.create({
            "Booking Nr.": reservation_id,
            "Customer Name": full_name,
            "Date Trip": date_trip,
            "trip Name": product_name,
            "Agency": "Tiqets",
            "Total Travelers": total_quantity
            # Removed Notes field temporarily to avoid 422 Unknown Field error
        })
        
        # تجهيز الرد
        response_data = {
            "reservation_id": reservation_id,
            "expires_at": (datetime.datetime.utcnow() + datetime.timedelta(minutes=30)).isoformat() + "Z"
        }
        
        # إضافة الأسعار إن وجدت
        if product_fields.get("Provides Pricing"):
            unit_price = {}
            for t in tickets:
                var_id = t["variant_id"]
                price_amount = product_fields.get("Adult Price" if var_id == "ADT" else "Child Price", "0")
                unit_price[var_id] = {
                    "amount": str(price_amount),
                    "currency": product_fields.get("Currency", "USD")
                }
            response_data["unit_price"] = unit_price
            
        return jsonify(response_data), 200

    except Exception as e:
        print(f"Error in make_reservation: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# ==========================================
# ✅ 4. تأكيد الحجز وسحب التذاكر (Booking)
# ==========================================
@app.route('/v2/booking', methods=['POST'])
def confirm_booking():
    try:
        data = request.json
        reservation_id = data.get("reservation_id")
        order_reference = data.get("order_reference")
        
        if not reservation_id:
            return jsonify({"error_code": 1000, "error": "Missing argument", "message": "Required argument reservation_id was not found"}), 400
            
        # 1. البحث عن الحجز المبدئي في جدول List
        booking_records = list_table.all(formula=match({"Booking Nr.": reservation_id}))
        if not booking_records:
            return jsonify({"error_code": 3002, "error": "Incorrect reservation ID", "message": "Given reservation ID is incorrect"}), 400
            
        list_record = booking_records[0]
        list_record_id = list_record["id"]
        product_name = list_record["fields"].get("trip Name")
        total_travelers = list_record["fields"].get("Total Travelers", 1)
        
        # 2. تحديد جدول التذاكر والـ View من الكتالوج
        product_records = catalog_table.all(formula=match({"Product Name": product_name}))
        if not product_records:
            return jsonify({"error": "Product configuration missing in catalog"}), 500
            
        product_fields = product_records[0]["fields"]
        tickets_table_name = product_fields.get("Tickets Table Name", "Grand_Tickets")
        tickets_view_name = product_fields.get("Ticket View Name", "Tiqet") # تم تصحيح الاسم هنا
        
        tickets_table = api.table(TICKETS_BASE_ID, tickets_table_name)
        
        # 3. سحب التذاكر المتاحة (حيث حقل Booking فارغ)
        # نستخدم الـ View المخصص الذي يحتوي فقط على تذاكر هذه الرحلة
        available_tickets = tickets_table.all(
            view=tickets_view_name,
            formula="{Booking}=''", # نفترض أن حقل الربط اسمه Booking، إذا كان فارغاً يعني متاح
            max_records=total_travelers
        )
        
        if len(available_tickets) < total_travelers:
            return jsonify({"error_code": 3000, "error": "Availability error", "message": "Not enough tickets available in the pool"}), 400
            
        # التحقق مما إذا كانت الرحلة تتطلب Audio Guide
        has_audio_guide = product_fields.get("Has Audio Guide", False)
            
        # 4. ربط التذاكر بالحجز وجمع الباركودات
        barcodes = []
        for ticket in available_tickets:
            ticket_id = ticket["id"]
            # نربط التذكرة برقم الحجز النهائي (كنص لأن الجدول في Base مختلف)
            tickets_table.update(ticket_id, {"Booking": order_reference})
            
            # جلب الباركود أو الرابط (التذكرة الأساسية)
            t_fields = ticket["fields"]
            barcode_val = t_fields.get("QR URL") or t_fields.get("Ticket Code") or t_fields.get("PDF Link") or "UNKNOWN_BARCODE"
            barcodes.append(barcode_val)
            
            # إذا كان هناك Audio Guide، نضيف الرابط كباركود إضافي لنفس الشخص
            if has_audio_guide:
                # Use order_reference for the app link as it's the final confirmed ID
                audio_guide_url = f"http://tiqets.ftstravels.net/?GM/ticketId={order_reference}"
                barcodes.append(audio_guide_url)
            
        # تحديث الحجز في List: استبدال رقم الحجز المؤقت برقم Tiqets النهائي وتحديث الملاحظات
        list_table.update(list_record_id, {
            "Booking Nr.": order_reference
            # Removed "Notes" update to avoid 422
        })
        
        # 5. إرسال الرد لـ Tiqets
        # Tiqets تدعم 1 barcode للطلب كله، أو 1 barcode لكل تذكرة. سنرسل 1 لكل تذكرة.
        response_data = {
            "booking_id": order_reference,
            "barcode_format": "QRCODE", # أو PDF بناءً على ما لديك
            "barcode_scope": "ticket",
            "tickets": {
                "ADT": barcodes # نرسل جميع الباركودات تحت فئة واحدة مؤقتاً، يمكن تخصيصها لاحقاً
            }
        }
        
        return jsonify(response_data), 200

    except Exception as e:
        print(f"Error in confirm_booking: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# ==========================================
# ❌ 5. الإلغاء (Cancellation)
# ==========================================
@app.route('/v2/booking/<booking_id>', methods=['DELETE'])
def cancel_booking(booking_id):
    try:
        # 1. البحث عن الحجز في جدول List
        booking_records = list_table.all(formula=match({"Booking Nr.": booking_id}))
        if not booking_records:
            return jsonify({"error_code": 1004, "error": "Missing booking", "message": f"Booking with ID {booking_id} doesn't exist"}), 400
            
        list_record = booking_records[0]
        list_record_id = list_record["id"]
        product_name = list_record["fields"].get("trip Name")
        
        # 2. تحديد جدول التذاكر لفك الربط
        product_records = catalog_table.all(formula=match({"Product Name": product_name}))
        if product_records:
            tickets_table_name = product_records[0]["fields"].get("Tickets Table Name", "Grand_Tickets")
            tickets_table = api.table(TICKETS_BASE_ID, tickets_table_name)
            
            # البحث عن التذاكر المربوطة بهذا الحجز وفك ربطها (إرجاعها للمخزون)
            linked_tickets = tickets_table.all(formula=f"FIND('{booking_id}', {{Booking}})")
            for ticket in linked_tickets:
                tickets_table.update(ticket["id"], {"Booking": ""}) # تفريغ الحقل النصي
                
        # 3. إلغاء الحجز في جدول List (أو حذفه)
        # بدلاً من الحذف النهائي، نحدث الملاحظات ليكون ملغى
        list_table.update(list_record_id, {
            "Notes": f"{list_record['fields'].get('Notes', '')} | STATUS: CANCELLED"
        })
        # أو يمكن استخدام: list_table.delete(list_record_id)
        
        return '', 204

    except Exception as e:
        print(f"Error in cancel_booking: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# ==========================================
# 🩺 نقطة فحص الصحة (Health Check)
# ==========================================
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "Tiqets API is running"}), 200


if __name__ == '__main__':
    # تشغيل السيرفر على البورت 5005 (يمكنك تغييره)
    app.run(host='0.0.0.0', port=5005, debug=True)
