import os
import json
import time
from runtime.pi_brain.background_task_engine import BackgroundTaskEngine

def run_watcher_test():
    print("=== Testing Real Watcher Execution on '123456test' ===")
    
    user_dir = "runtime/pi_brain/users/u_ahmady"
    outbox_dir = os.path.join(user_dir, "bridge", "outbox")
    inbox_dir = os.path.join(user_dir, "bridge", "inbox")
    watchers_dir = os.path.join(user_dir, "management", "watchers")
    
    os.makedirs(outbox_dir, exist_ok=True)
    os.makedirs(watchers_dir, exist_ok=True)
    
    # تنظيف الـ outbox القديم
    for f in os.listdir(outbox_dir):
        os.remove(os.path.join(outbox_dir, f))
        
    print("\n[1] Creating an add_watcher manifest...")
    # سنراقب حقل 'Invoice Status' ليكون 'pending' (الذي نعرف أنه موجود في الحجز الآن)
    watcher_manifest = {
        "manifest_id": "man_watch_123456",
        "intent": "add_test_watcher",
        "actions": [
            {
                "type": "add_watcher",
                "target_record": "recPRC2TeFZTc8gOE", # Record ID for 123456test
                "target_base": "main",
                "condition_field": "Invoice Status",
                "condition_value": "pending",
                "requires_approval": False,
                "action_on_trigger": "send_internal_notification_invoice_pending"
            }
        ]
    }
    
    with open(os.path.join(outbox_dir, "man_watch_123456.json"), "w") as f:
        json.dump(watcher_manifest, f, indent=2)
        
    print("    Manifest placed in outbox.")
    
    print("\n[2] Starting Background Task Engine (will run 1 cycle)...")
    engine = BackgroundTaskEngine(check_interval=2)
    engine.start()
    
    print("    Waiting 5 seconds for engine to process outbox and check watchers...")
    time.sleep(5)
    
    engine.stop()
    
    print("\n[3] Checking Results...")
    
    # 1. هل تم تفريغ الـ outbox؟
    outbox_files = os.listdir(outbox_dir)
    print(f"    Outbox files remaining: {len(outbox_files)}")
    if outbox_files:
        print(f"    Warning: Outbox not empty! -> {outbox_files}")
        
    # 2. هل تم توليد manifest جديد (Triggered) في الـ outbox لأن الشرط تحقق؟
    triggered_files = [f for f in outbox_files if f.startswith("man_triggered_")]
    if triggered_files:
        print(f"    SUCCESS! Triggered manifest found: {triggered_files[0]}")
        with open(os.path.join(outbox_dir, triggered_files[0]), "r") as f:
            print(json.dumps(json.load(f), indent=2))
    else:
        print("    No triggered manifest found in outbox.")
        # ربما مازال الـ watcher موجوداً إذا لم يتحقق الشرط؟
        watcher_files = os.listdir(watchers_dir)
        print(f"    Watchers remaining: {len(watcher_files)}")

if __name__ == "__main__":
    run_watcher_test()