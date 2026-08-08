import os
import json
import time
from runtime.pi_brain.background_task_engine import BackgroundTaskEngine
from runtime.pi_brain.knowledge_engine import KnowledgeEngine

def run_simulation():
    print("=== PI Workspace OS Simulation ===")
    
    # 1. إعداد المسارات
    user_key = "u_ahmady"
    user_dir = f"runtime/pi_brain/users/{user_key}"
    outbox_dir = os.path.join(user_dir, "bridge", "outbox")
    inbox_dir = os.path.join(user_dir, "bridge", "inbox")
    
    os.makedirs(outbox_dir, exist_ok=True)
    os.makedirs(inbox_dir, exist_ok=True)
    
    # 2. محاكاة: PI يقرأ القواعد و الـ Schema
    print("\n[1] PI is thinking... Reading Knowledge Base...")
    ke = KnowledgeEngine()
    schema = ke.get_action_schema("create_invoice")
    print(f"    Loaded Schema for 'create_invoice': {schema.get('description')}")
    
    # 3. محاكاة: PI يقوم بتوليد الـ Manifest بناءً على الـ Schema
    print("\n[2] PI generated a Manifest and placing it in Outbox...")
    manifest_id = f"man_sim_{int(time.time())}"
    simulated_manifest = {
        "manifest_id": manifest_id,
        "intent": "create_test_invoice_and_watcher",
        "actions": [
            {
                "type": "create_invoice",
                "target_record": "rec_simulate_123",
                "requires_approval": True,
                "payload": {
                    "amount": 250,
                    "currency": "USD",
                    "provider": "Stripe"
                }
            },
            {
                "type": "add_watcher",
                "target_base": "main",
                "condition": "status == 'paid'",
                "requires_approval": False,
                "action_on_trigger": "send_welcome_message"
            }
        ]
    }
    
    manifest_path = os.path.join(outbox_dir, f"{manifest_id}.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(simulated_manifest, f, indent=2)
        
    print(f"    Manifest saved at: {manifest_path}")
    
    # 4. تشغيل المحرك الخلفي
    print("\n[3] Background Task Engine is waking up to process the Outbox...")
    engine = BackgroundTaskEngine(check_interval=2)
    engine.start()
    
    # ننتظر قليلاً ليعمل المحرك
    time.sleep(4)
    engine.stop()
    
    # 5. التحقق من النتيجة في الـ Inbox
    print("\n[4] PI is checking Inbox for results...")
    result_path = os.path.join(inbox_dir, f"result_{manifest_id}.json")
    
    if os.path.exists(result_path):
        with open(result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        print("    Success! The Engine processed the Manifest.")
        print(f"    Result details:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
    else:
        print("    Failed to find the result in Inbox. Something went wrong.")

if __name__ == "__main__":
    run_simulation()
