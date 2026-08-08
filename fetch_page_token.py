import json
import requests
import sys

config_path = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\config.json"
try:
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
except Exception as e:
    print(f"Error loading config: {e}")
    sys.exit(1)

page_access_token = config.get("facebook", {}).get("page_access_token")
target_page_id = config.get("facebook", {}).get("page_id")

if not page_access_token:
    print("No page_access_token found in config.json")
    sys.exit(1)

url = f"https://graph.facebook.com/v19.0/me/accounts?access_token={page_access_token}"
response = requests.get(url)

if response.status_code != 200:
    print(f"Error fetching accounts: {response.text}")
    sys.exit(1)

data = response.json().get("data", [])
found = False

print("\n--- الصفحات المتاحة لهذا التوكن ---")
for page in data:
    print(f"اسم الصفحة: {page.get('name')}")
    print(f"معرف الصفحة (ID): {page.get('id')}")
    if page.get("id") == target_page_id:
        found = True
        print("\n✅ تم العثور على الصفحة المطلوبة!")
        print("الـ Page Access Token الخاص بها هو:")
        print(page.get("access_token"))
        
        # Update config.json automatically
        config["facebook"]["page_access_token"] = page.get("access_token")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print("\nتم تحديث ملف config.json بالتوكن الصحيح للصفحة تلقائياً!")
    print("-" * 30)

if not found:
    print(f"\n❌ لم يتم العثور على الصفحة ذات المعرف {target_page_id} ضمن صلاحيات هذا التوكن.")
    print("يرجى التأكد من إضافة الصفحة (Add Assets -> Pages) للمستخدم النظامي (System User) في إعدادات مدير الأعمال.")
