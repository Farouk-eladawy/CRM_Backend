import json
import hashlib
import time
import requests
import os
from dotenv import load_dotenv
from datetime import datetime
from flask import Flask, request, jsonify
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

load_dotenv()

app = Flask(__name__)

# ==============================================================================
# إعدادات Airtable
# ==============================================================================
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = "List"

def save_to_airtable(order_data):
    """
    حفظ الحجز القادم من Trip.com في Airtable
    """
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        print("Airtable credentials are missing. Cannot save to Airtable.")
        return None

    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }

    # استخراج البيانات الأساسية من طلب Trip.com (بناءً على التوثيق)
    # ملاحظة: قد تختلف أسماء الحقول بناءً على التوثيق الفعلي للـ JSON القادم
    ota_order_id = order_data.get('otaOrderId', '')
    product_name = order_data.get('productName', 'Trip.com Booking')
    guest_name = order_data.get('contactPerson', {}).get('name', 'Unknown Guest')
    guest_phone = order_data.get('contactPerson', {}).get('mobile', '')
    use_date = order_data.get('useDate', '')
    quantity = order_data.get('quantity', 1)
    
    # تحضير البيانات لـ Airtable (يجب مطابقة هذه الحقول مع حقول جدولك الفعلي)
    airtable_data = {
        "records": [
            {
                "fields": {
                    "Name": guest_name,
                    "Phone": guest_phone,
                    "Booking Number": ota_order_id,
                    "Supplier": "Trip.com",
                    "Status": "Confirmed",
                    "Tour/Service": product_name,
                    "Date": use_date,
                    "Pax": str(quantity),
                    "Notes": f"Auto-imported from Trip.com API. Order ID: {ota_order_id}"
                }
            }
        ],
        "typecast": True
    }

    try:
        response = requests.post(url, headers=headers, json=airtable_data)
        response.raise_for_status()
        print(f"Successfully saved Trip.com order {ota_order_id} to Airtable.")
        return response.json().get('records', [{}])[0].get('id')
    except Exception as e:
        print(f"Error saving to Airtable: {e}")
        if hasattr(e, 'response') and e.response:
            print("Airtable response:", e.response.text)
        return None

# ==============================================================================
# إعدادات التشفير الخاصة بـ Trip.com
# ==============================================================================
# هذه المفاتيح ستحصل عليها من صفحة Sandbox / Production في لوحة تحكم Trip.com
TRIP_API_ACCOUNT = "f1f90aaa4db57f12"
TRIP_SIGNKEY = "ed66163a8b05ce2f82b0bbaaacb93d96"  # API key from the dashboard
TRIP_AES_KEY = "50541e40a3e57d96"  # 16 digits
TRIP_AES_IV = "645fb8e2d4afa7c3"    # 16 digits


def encode_bytes(data: bytes) -> str:
    """تحويل البايتات إلى نظام الـ Hex المخصص لـ Trip (أحرف من a إلى p)"""
    res = []
    for b in data:
        res.append(chr(((b >> 4) & 0xF) + ord('a')))
        res.append(chr((b & 0xF) + ord('a')))
    return "".join(res)

def decode_bytes(s: str) -> bytes:
    """عكس التحويل من نظام الـ Hex المخصص إلى بايتات"""
    res = bytearray()
    for i in range(0, len(s), 2):
        high = (ord(s[i]) - ord('a')) << 4
        low = ord(s[i+1]) - ord('a')
        res.append(high + low)
    return bytes(res)

def encrypt_body(data_str: str, secret_key: str, iv: str) -> str:
    """تشفير الـ Body باستخدام AES-128-CBC"""
    cipher = AES.new(secret_key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
    encrypted = cipher.encrypt(pad(data_str.encode('utf-8'), AES.block_size))
    return encode_bytes(encrypted)

def decrypt_body(encrypted_str: str, secret_key: str, iv: str) -> str:
    """فك تشفير الـ Body القادم من Trip.com"""
    cipher = AES.new(secret_key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
    encrypted_bytes = decode_bytes(encrypted_str)
    original_bytes = unpad(cipher.decrypt(encrypted_bytes), AES.block_size)
    return original_bytes.decode('utf-8')

def generate_signature(account_id, service_name, request_time, encrypted_body, version, signkey):
    """توليد التوقيع الرقمي للتحقق من صحة الطلب"""
    raw_str = f"{account_id}{service_name}{request_time}{encrypted_body}{version}{signkey}"
    return hashlib.md5(raw_str.encode('utf-8')).hexdigest().lower()

def generate_success_response(header, body_dict):
    """دالة مساعدة لتوليد الرد المشفر بنجاح"""
    response_body_str = json.dumps(body_dict)
    res_encrypted_body = encrypt_body(response_body_str, TRIP_AES_KEY, TRIP_AES_IV)
    res_request_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    res_sign = generate_signature(
        header.get('accountId'),
        header.get('serviceName'),
        res_request_time,
        res_encrypted_body,
        header.get('version'),
        TRIP_SIGNKEY
    )
    
    return jsonify({
        "header": {
            "accountId": header.get('accountId'),
            "serviceName": header.get('serviceName'),
            "requestTime": res_request_time,
            "version": header.get('version'),
            "sign": res_sign
        },
        "body": res_encrypted_body
    })

def generate_error_response(code, msg):
    """دالة مساعدة لتوليد رد الخطأ"""
    return jsonify({"returnCode": code, "returnMsg": msg}), 400

# ==============================================================================
# Endpoints (مسارات استقبال الطلبات من Trip.com)
# ==============================================================================

@app.route('/trip/CreateOrder.do', methods=['POST'])
def trip_create_order():
    """
    هذا المسار سيتم استدعاؤه من Trip.com لإنشاء حجز جديد
    """
    try:
        data = request.json
        header = data.get('header', {})
        encrypted_body = data.get('body', '')
        
        # 1. التحقق من التوقيع الرقمي (للتأكد أن الطلب من Trip.com فعلاً)
        expected_sign = generate_signature(
            header.get('accountId'),
            header.get('serviceName'),
            header.get('requestTime'),
            encrypted_body,
            header.get('version'),
            TRIP_SIGNKEY
        )
        
        if expected_sign != header.get('sign'):
            return jsonify({"returnCode": "1001", "returnMsg": "Invalid Signature"}), 400
            
        # 2. فك تشفير البيانات أو التعامل معها مباشرة إذا لم تكن مشفرة
        if isinstance(encrypted_body, str):
            decrypted_body_str = decrypt_body(encrypted_body, TRIP_AES_KEY, TRIP_AES_IV)
            order_data = json.loads(decrypted_body_str)
        else:
            order_data = encrypted_body
            encrypted_body = json.dumps(encrypted_body, separators=(',', ':'))
            
        print("Received Order Data:", json.dumps(order_data, indent=2))
        
        # ==========================================
        # 2.5 حفظ الحجز في Airtable
        # ==========================================
        airtable_record_id = save_to_airtable(order_data)
        
        # 3. تجهيز الرد بالنجاح وتشفيره
        response_body = {
            "orderId": order_data.get('otaOrderId'), # رقم الطلب في Trip
            "supplierOrderId": airtable_record_id if airtable_record_id else f"FTS-{int(time.time())}", # رقم الطلب في نظامك
            "orderStatus": "CONFIRMED" # حالة الطلب
        }
        
        return generate_success_response(header, response_body)

    except Exception as e:
        print("Error processing Trip.com request:", str(e))
        return generate_error_response("1002", "System Error")

@app.route('/trip/CreatePreOrder.do', methods=['POST'])
def trip_create_preorder():
    """مسار إنشاء حجز مبدئي (Pre-Order)"""
    try:
        data = request.json
        header = data.get('header', {})
        encrypted_body = data.get('body', '')
        
        # 2. فك تشفير البيانات أو التعامل معها مباشرة إذا لم تكن مشفرة
        if isinstance(encrypted_body, str):
            decrypted_body_str = decrypt_body(encrypted_body, TRIP_AES_KEY, TRIP_AES_IV)
            order_data = json.loads(decrypted_body_str)
        else:
            # إذا كان الـ body عبارة عن JSON مباشرة (كما يظهر في بعض Logs الاختبارات)
            order_data = encrypted_body
            encrypted_body = json.dumps(encrypted_body, separators=(',', ':')) # لإعادة استخدامه في التوقيع إذا لزم الأمر
            
        print("Received Pre-Order Data:", json.dumps(order_data, indent=2))
        
        response_body = {
            "orderId": order_data.get('otaOrderId'),
            "supplierOrderId": f"PRE-{int(time.time())}", 
            "orderStatus": "CONFIRMED"
        }
        return generate_success_response(header, response_body)
    except Exception as e:
        return generate_error_response("1002", "System Error")

@app.route('/trip/CancelOrder.do', methods=['POST'])
def trip_cancel_order():
    """مسار إلغاء الحجز"""
    try:
        data = request.json
        header = data.get('header', {})
        encrypted_body = data.get('body', '')
        
        if isinstance(encrypted_body, str):
            decrypted_body_str = decrypt_body(encrypted_body, TRIP_AES_KEY, TRIP_AES_IV)
            order_data = json.loads(decrypted_body_str)
        else:
            order_data = encrypted_body
            encrypted_body = json.dumps(encrypted_body, separators=(',', ':'))
        print("Received Cancel Order Data:", json.dumps(order_data, indent=2))
        
        response_body = {
            "orderId": order_data.get('otaOrderId'),
            "supplierOrderId": order_data.get('supplierOrderId', f"FTS-{int(time.time())}"),
            "cancelStatus": "SUCCESS"
        }
        return generate_success_response(header, response_body)
    except Exception as e:
        return generate_error_response("1002", "System Error")

@app.route('/trip/CancelPreOrder.do', methods=['POST'])
def trip_cancel_preorder():
    """مسار إلغاء الحجز المبدئي"""
    try:
        data = request.json
        header = data.get('header', {})
        encrypted_body = data.get('body', '')
        
        if isinstance(encrypted_body, str):
            decrypted_body_str = decrypt_body(encrypted_body, TRIP_AES_KEY, TRIP_AES_IV)
            order_data = json.loads(decrypted_body_str)
        else:
            order_data = encrypted_body
            encrypted_body = json.dumps(encrypted_body, separators=(',', ':'))
        print("Received Cancel Pre-Order Data:", json.dumps(order_data, indent=2))
        
        response_body = {
            "orderId": order_data.get('otaOrderId'),
            "supplierOrderId": order_data.get('supplierOrderId', f"PRE-{int(time.time())}"),
            "cancelStatus": "SUCCESS"
        }
        return generate_success_response(header, response_body)
    except Exception as e:
        return generate_error_response("1002", "System Error")

@app.route('/trip/QueryOrder.do', methods=['POST'])
def trip_query_order():
    """مسار الاستعلام عن حالة الحجز"""
    try:
        data = request.json
        header = data.get('header', {})
        encrypted_body = data.get('body', '')
        
        if isinstance(encrypted_body, str):
            decrypted_body_str = decrypt_body(encrypted_body, TRIP_AES_KEY, TRIP_AES_IV)
            order_data = json.loads(decrypted_body_str)
        else:
            order_data = encrypted_body
            encrypted_body = json.dumps(encrypted_body, separators=(',', ':'))
        print("Received Query Order Data:", json.dumps(order_data, indent=2))
        
        response_body = {
            "orderId": order_data.get('otaOrderId'),
            "supplierOrderId": order_data.get('supplierOrderId', f"FTS-{int(time.time())}"),
            "orderStatus": "CONFIRMED"
        }
        return generate_success_response(header, response_body)
    except Exception as e:
        return generate_error_response("1002", "System Error")

@app.route('/trip/PayPreOrder.do', methods=['POST'])
def trip_pay_preorder():
    """مسار دفع الحجز المبدئي"""
    try:
        data = request.json
        header = data.get('header', {})
        encrypted_body = data.get('body', '')
        
        if isinstance(encrypted_body, str):
            decrypted_body_str = decrypt_body(encrypted_body, TRIP_AES_KEY, TRIP_AES_IV)
            order_data = json.loads(decrypted_body_str)
        else:
            order_data = encrypted_body
            encrypted_body = json.dumps(encrypted_body, separators=(',', ':'))
        print("Received Pay Pre-Order Data:", json.dumps(order_data, indent=2))
        
        response_body = {
            "orderId": order_data.get('otaOrderId'),
            "supplierOrderId": order_data.get('supplierOrderId', f"FTS-{int(time.time())}"),
            "orderStatus": "CONFIRMED"
        }
        return generate_success_response(header, response_body)
    except Exception as e:
        return generate_error_response("1002", "System Error")

if __name__ == '__main__':
    # تشغيل السيرفر على بورت 5006
    app.run(host='0.0.0.0', port=5006, debug=True)
