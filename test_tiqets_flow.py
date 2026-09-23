import requests
import json
import time

import tiqets_api as t

BASE_URL = "http://127.0.0.1:5005"
HEADERS = {
    "API-Key": t.resolve_tiqets_api_key(t.load_tiqets_config()),
    "Content-Type": "application/json",
}

def print_step(step_name):
    print(f"\n{'='*50}\n▶️ STEP: {step_name}\n{'='*50}")

def run_test():
    try:
        # 1. اختبار مسار المنتجات
        print_step("1. Fetching Products Catalog")
        resp = requests.get(f"{BASE_URL}/v2/products", headers=HEADERS)
        print(f"Status Code: {resp.status_code}")
        products = resp.json()
        print(json.dumps(products, indent=2))
        
        if not products:
            print("❌ No products found in catalog. Please add at least one product in Airtable to continue testing.")
            return
            
        target_product_id = products[0]["id"]
        print(f"✅ Selected Product ID for testing: {target_product_id}")
        
        # 2. اختبار مسار التوافر (لليوم ولمدة 3 أيام قادمة)
        print_step(f"2. Checking Availability for {target_product_id}")
        import datetime
        start_date = datetime.date.today().strftime("%Y-%m-%d")
        end_date = (datetime.date.today() + datetime.timedelta(days=3)).strftime("%Y-%m-%d")
        
        resp = requests.get(
            f"{BASE_URL}/v2/products/{target_product_id}/availability",
            headers=HEADERS,
            params={"start": start_date, "end": end_date}
        )
        print(f"Status Code: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))
        
        # 3. اختبار مسار الحجز المبدئي (Reservation)
        print_step(f"3. Creating Reservation for {target_product_id}")
        reservation_payload = {
            "datetime": f"{start_date}T10:00",
            "tickets": [
                {"variant_id": "ADT", "quantity": 1}
            ],
            "customer": {
                "first_name": "Test",
                "last_name": "User",
                "email": "test.tiqets@example.com",
                "phone": "+201000000000",
                "country": "eg"
            }
        }
        
        resp = requests.post(
            f"{BASE_URL}/v2/products/{target_product_id}/reservation",
            headers=HEADERS,
            json=reservation_payload
        )
        print(f"Status Code: {resp.status_code}")
        res_data = resp.json()
        print(json.dumps(res_data, indent=2))
        
        if resp.status_code != 200:
            print("❌ Reservation failed. Cannot proceed to booking.")
            return
            
        reservation_id = res_data.get("reservation_id")
        print(f"✅ Reservation successful! Reservation ID: {reservation_id}")
        
        print("\n⏳ Waiting 3 seconds before confirming booking...")
        time.sleep(3)
        
        # 4. اختبار مسار تأكيد الحجز (Booking)
        print_step("4. Confirming Booking (Pulling Tickets)")
        booking_payload = {
            "reservation_id": reservation_id,
            "order_reference": "TIQ-TEST-999"
        }
        
        resp = requests.post(
            f"{BASE_URL}/v2/booking",
            headers=HEADERS,
            json=booking_payload
        )
        print(f"Status Code: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))
        
        if resp.status_code == 200:
            print(f"\n🎉 SUCCESS! Full flow completed. Check Airtable List table for Reservation: {reservation_id}")
        else:
            print("\n❌ Booking confirmation failed.")

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")

if __name__ == "__main__":
    run_test()
