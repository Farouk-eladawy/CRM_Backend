import logging
import sys
import os

# Ensure we can import ai_agent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from ai_agent import AIAgent

logging.basicConfig(level=logging.INFO)

def test_cancellation_workflow():
    try:
        agent = AIAgent()
        
        customer_name = "Test Customer (اختبار النظام)"
        b_nr = "TEST-123456"
        b_dest = "Hurghada/Cairo"
        message_body = "أريد إلغاء رحلتي من فضلك (رسالة اختبار)"
        
        notify_msg = f"🚨 *طلب إلغاء عاجل* 🚨\nالعميل: {customer_name}\nرقم الحجز: {b_nr}\nالوِجهة: {b_dest}\nالرسالة: {message_body}"
        
        target_employees = [
            "201027722684", # Abdelrahman Sayed
            "201129155520", # Ahmed Taha
            "201020711106"  # Hazem_Mohamed
        ]
        
        print(f"\n--- Testing Cancellation Notification Workflow ---")
        print(f"Message Content:\n{notify_msg}\n")
        
        for emp_phone in target_employees:
            print(f"Sending to {emp_phone}...")
            ok, err = agent.send_whatsapp_message(emp_phone, text=notify_msg, receiving_phone_id="201090005205")
            if ok:
                print(f"✅ Successfully sent to {emp_phone}")
            else:
                print(f"❌ Failed to send to {emp_phone}. Error: {err}")
                
    except Exception as e:
        print(f"❌ Error during test: {e}")

if __name__ == "__main__":
    test_cancellation_workflow()
