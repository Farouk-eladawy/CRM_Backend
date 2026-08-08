import os
import json
import time
from runtime.pi_brain.knowledge_engine import KnowledgeEngine

def run_learning_test():
    print("=== Testing Self-Learning (Knowledge & Recovery Engine) ===")
    
    user_key = "u_ahmady"
    user_dir = f"runtime/pi_brain/users/{user_key}"
    inbox_dir = os.path.join(user_dir, "bridge", "inbox")
    memory_dir = os.path.join(user_dir, "memory")
    patterns_path = os.path.join(memory_dir, "patterns.json")
    
    os.makedirs(inbox_dir, exist_ok=True)
    os.makedirs(memory_dir, exist_ok=True)
    
    # 1. إنشاء نتيجتين وهميتين (واحدة نجاح وواحدة فشل)
    print("\n[1] Creating simulated inbox results (1 Success, 1 Failure)...")
    
    success_result = {
        "manifest_id": "man_success_777",
        "status": "success",
        "executed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "actions_results": [{"action_type": "create_invoice", "status": "executed"}]
    }
    
    fail_result = {
        "manifest_id": "man_fail_888",
        "status": "failed",
        "error": "Missing required field 'amount' in payload",
        "executed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    
    with open(os.path.join(inbox_dir, "result_man_success_777.json"), "w", encoding="utf-8") as f:
        json.dump(success_result, f, indent=2)
        
    with open(os.path.join(inbox_dir, "result_man_fail_888.json"), "w", encoding="utf-8") as f:
        json.dump(fail_result, f, indent=2)
        
    print("    Simulated results placed in Inbox.")
    
    # 2. تشغيل محرك المعرفة لقراءة الـ Inbox
    print("\n[2] Running KnowledgeEngine.process_inbox_feedback()...")
    engine = KnowledgeEngine()
    learned_count = engine.process_inbox_feedback(user_key)
    print(f"    Engine processed {learned_count} new lessons.")
    
    # 3. التحقق من التحديث في patterns.json
    print("\n[3] Checking memory/patterns.json for updates...")
    if os.path.exists(patterns_path):
        with open(patterns_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        lessons = data.get("lessons", []) if isinstance(data, dict) else data
        print(f"    Total lessons in memory: {len(lessons)}")
        
        # طباعة آخر درسين
        print("    Recent Lessons Learned:")
        for lesson in lessons[-2:]:
            print(f"      - ID: {lesson.get('manifest_id')} | Status: {lesson.get('status')}")
            print(f"        Observation: {lesson.get('observation')}")
    else:
        print("    Failed: patterns.json not found!")

if __name__ == "__main__":
    run_learning_test()
