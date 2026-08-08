import sys
import os
import json
from pyairtable import Api
from datetime import datetime

# إعدادات Airtable (يفضل وضعها في متغيرات بيئة)
# استبدل القيم أدناه بالقيم الحقيقية من كودك القديم أو ملف .env
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY", "YOUR_API_KEY_HERE")
BASE_ID = os.getenv("AIRTABLE_BASE_ID", "YOUR_BASE_ID_HERE")
TABLE_NAME = "Leads"  # تأكد من اسم الجدول

def add_lead(name, phone, email, notes=""):
    if not AIRTABLE_API_KEY or not BASE_ID:
        print("Error: Airtable API Key or Base ID missing.")
        return

    try:
        api = Api(AIRTABLE_API_KEY)
        table = api.table(BASE_ID, TABLE_NAME)
        
        record = table.create({
            "Name": name,
            "Phone": phone,
            "Email": email,
            "Notes": notes,
            "Date": datetime.now().isoformat()
        })
        
        print(f"✅ Lead added successfully! Record ID: {record['id']}")
        
    except Exception as e:
        print(f"Error adding lead to Airtable: {e}")

if __name__ == "__main__":
    # نتوقع المدخلات كـ JSON string من سطر الأوامر لتسهيل التمرير
    # Usage: python add_lead.py '{"name": "Ali", "phone": "123", "email": "a@a.com"}'
    
    if len(sys.argv) < 2:
        print("Usage: python add_lead.py '<json_data>'")
    else:
        try:
            data_str = sys.argv[1]
            data = json.loads(data_str)
            
            add_lead(
                name=data.get("name", "Unknown"),
                phone=data.get("phone", ""),
                email=data.get("email", ""),
                notes=data.get("notes", "")
            )
        except json.JSONDecodeError:
            print("Error: Invalid JSON input.")
        except Exception as e:
            print(f"Error: {e}")
