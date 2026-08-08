import os
import json
import time
from runtime.pi_brain.background_task_engine import BackgroundTaskEngine

def run_schedule_test():
    print("=== Testing Real Scheduled Task Execution ===")
    
    user_dir = "runtime/pi_brain/users/u_ahmady"
    outbox_dir = os.path.join(user_dir, "bridge", "outbox")
    tasks_dir = os.path.join(user_dir, "management", "scheduled_tasks")
    
    os.makedirs(outbox_dir, exist_ok=True)
    os.makedirs(tasks_dir, exist_ok=True)
    
    # تنظيف الـ outbox القديم
    for f in os.listdir(outbox_dir):
        os.remove(os.path.join(outbox_dir, f))
        
    print("\n[1] Creating a schedule_task manifest...")
    # سننشئ مهمة يتم تنفيذها بعد 3 ثواني من الآن
    schedule_manifest = {
        "manifest_id": "man_sched_test_1",
        "intent": "add_test_schedule",
        "actions": [
            {
                "type": "schedule_task",
                "execute_at": "+3 sec",
                "action_to_execute": {
                    "type": "send_reminder_message",
                    "target_record": "recPRC2TeFZTc8gOE",
                    "payload": {
                        "message": "This is a scheduled reminder!"
                    }
                },
                "requires_approval": False
            }
        ]
    }
    
    with open(os.path.join(outbox_dir, "man_sched_test_1.json"), "w") as f:
        json.dump(schedule_manifest, f, indent=2)
        
    print("    Manifest placed in outbox. execute_at: +3 sec")
    
    print("\n[2] Starting Background Task Engine (Monitoring for 6 seconds)...")
    engine = BackgroundTaskEngine(check_interval=2)
    engine.start()
    
    print("    Waiting 6 seconds for engine to process outbox, register task, wait for time, and execute...")
    time.sleep(6)
    
    engine.stop()
    
    print("\n[3] Checking Results...")
    
    # 1. هل تم تفريغ الـ outbox من الطلب الأصلي؟
    outbox_files = os.listdir(outbox_dir)
    print(f"    Outbox files remaining: {len(outbox_files)}")
        
    # 2. هل تم توليد manifest جديد (Triggered) في الـ outbox لأن الوقت حان؟
    triggered_files = [f for f in outbox_files if f.startswith("man_scheduled_")]
    if triggered_files:
        print(f"    SUCCESS! Scheduled manifest generated: {triggered_files[0]}")
        with open(os.path.join(outbox_dir, triggered_files[0]), "r") as f:
            print(json.dumps(json.load(f), indent=2))
    else:
        print("    No scheduled manifest found in outbox.")
        tasks_files = os.listdir(tasks_dir)
        print(f"    Tasks remaining in queue: {len(tasks_files)}")

if __name__ == "__main__":
    run_schedule_test()