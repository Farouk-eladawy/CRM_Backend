import os
import json
import logging

logger = logging.getLogger(__name__)

class KnowledgeEngine:
    """
    محرك المعرفة (Knowledge Engine)
    يُستخدم من قبل PI لـ:
    1. قراءة قواعد النظام (System Rules) من ملفات .md
    2. استخراج هياكل التنفيذ (Schemas) لإنشاء الـ Manifests بشكل صحيح
    3. استرجاع الذاكرة التشغيلية (Operational Memory) من مساحة المستخدم
    """
    
    def __init__(self, base_dir=".", pi_brain_dir="runtime/pi_brain"):
        self.base_dir = base_dir
        self.pi_brain_dir = pi_brain_dir
        self.schemas_dir = os.path.join(self.pi_brain_dir, "schemas")
        
        # إنشاء مجلدات إذا لم تكن موجودة
        os.makedirs(self.schemas_dir, exist_ok=True)

    def read_system_rules(self, doc_paths=None):
        """
        يقرأ القواعد الأساسية للنظام من مستندات معينة.
        إذا لم يتم تحديد المستندات، سيقرأ الوثائق الافتراضية.
        """
        if not doc_paths:
            doc_paths = [
                ".trae/rules/ai agent.md",
                "PI_Workspace_Architecture_v1.md"
            ]
            
        rules_content = []
        for path in doc_paths:
            full_path = os.path.join(self.base_dir, path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        rules_content.append(f"--- Document: {path} ---\n" + f.read())
                except Exception as e:
                    logger.error(f"Error reading {path}: {e}")
                    
        return "\n\n".join(rules_content)

    def get_action_schema(self, action_type):
        """
        يجلب قالب التنفيذ (Schema) لإجراء معين ليتمكن PI من ملء البيانات بشكل صحيح.
        """
        schema_path = os.path.join(self.schemas_dir, f"{action_type}_schema.json")
        if os.path.exists(schema_path):
            try:
                with open(schema_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error reading schema {schema_path}: {e}")
        
        # قالب افتراضي إذا لم يوجد مخصص
        return {
            "type": action_type,
            "target_record": "string (record_id)",
            "requires_approval": "boolean",
            "payload": "object (key-value pairs)"
        }

    def get_user_memory(self, user_key, memory_type="patterns"):
        """
        يسترجع ذاكرة المستخدم (مثل patterns أو semantic) ليتعلم من الأخطاء السابقة.
        """
        memory_path = os.path.join(self.pi_brain_dir, "users", user_key, "memory", f"{memory_type}.json")
        if os.path.exists(memory_path):
            try:
                with open(memory_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error reading memory {memory_path}: {e}")
                
        return {}

    def get_all_action_schemas(self):
        """
        يجلب جميع قوالب التنفيذ (Schemas) المتاحة في النظام ليتيح لـ PI اختيار القالب المناسب.
        """
        all_schemas = {}
        if os.path.exists(self.schemas_dir):
            for filename in os.listdir(self.schemas_dir):
                if filename.endswith("_schema.json"):
                    schema_name = filename.replace("_schema.json", "")
                    schema_path = os.path.join(self.schemas_dir, filename)
                    try:
                        with open(schema_path, "r", encoding="utf-8") as f:
                            all_schemas[schema_name] = json.load(f)
                    except Exception as e:
                        logger.error(f"Error reading schema {schema_path}: {e}")
        return all_schemas

    def query_knowledge_db(self, user_request, limit=3):
        """
        يبحث في قاعدة المعرفة (knowledge.db) بطريقة Read-Only
        باستخدام الكلمات المفتاحية من طلب المستخدم لزيادة ذكاء PI.
        """
        if not user_request:
            return ""
            
        db_path = os.path.join(self.base_dir, "knowledge.db")
        if not os.path.exists(db_path):
            return ""
            
        try:
            import sqlite3
            import re
            
            # Extract simple words for search
            words = [w for w in re.findall(r'\w+', user_request.lower()) if len(w) > 2]
            if not words:
                return ""
            
            search_query = " OR ".join(words)
            
            # Connect in Read-Only mode
            uri = f"file:{db_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            results = []
            
            # Search Trips
            try:
                cursor.execute(
                    "SELECT title, description, itinerary, faqs FROM trips_fts WHERE trips_fts MATCH ? ORDER BY rank LIMIT ?",
                    (search_query, limit)
                )
                for row in cursor.fetchall():
                    results.append(f"[Trip Info] Title: {row['title']}\nDesc: {row['description']}\nItinerary: {row['itinerary']}\nFAQs: {row['faqs']}")
            except Exception as e:
                logger.error(f"Error querying trips_fts: {e}")
                
            # Search Documents
            try:
                cursor.execute(
                    "SELECT filename, department, content FROM documents_fts WHERE documents_fts MATCH ? ORDER BY rank LIMIT ?",
                    (search_query, limit)
                )
                for row in cursor.fetchall():
                    results.append(f"[Document] Name: {row['filename']} (Dept: {row['department']})\nContent: {row['content'][:500]}...")
            except Exception as e:
                logger.error(f"Error querying documents_fts: {e}")
                
            # Search QA Rules
            try:
                qa_query = f"%{'%'.join(words[:2])}%" # simple LIKE search
                cursor.execute(
                    "SELECT question, answer FROM strict_qa_rules WHERE question LIKE ? OR answer LIKE ? LIMIT ?",
                    (qa_query, qa_query, limit)
                )
                for row in cursor.fetchall():
                    results.append(f"[QA Rule] Q: {row['question']}\nA: {row['answer']}")
            except Exception as e:
                logger.error(f"Error querying strict_qa_rules: {e}")
                
            conn.close()
            
            if results:
                return "=== DYNAMIC KNOWLEDGE BASE (from knowledge.db) ===\n" + "\n\n".join(results) + "\n"
            return ""
        except Exception as e:
            logger.error(f"Failed to query knowledge.db: {e}")
            return ""

    def get_full_context_for_pi(self, user_key, action_intent=None, user_request=None):
        """
        يُجمّع السياق الشامل الذي يحتاجه PI قبل اتخاذ قرار أو كتابة Manifest.
        """
        context = {
            "system_rules": self.read_system_rules(),
            "dynamic_knowledge": self.query_knowledge_db(user_request),
            "user_patterns": self.get_user_memory(user_key, "patterns"),
            "user_semantic_knowledge": self.get_user_memory(user_key, "semantic"),
            "all_available_schemas": self.get_all_action_schemas()
        }

        if action_intent and action_intent != "agentic_orchestrator":
            context["required_schema"] = self.get_action_schema(action_intent)

        return context

    def process_inbox_feedback(self, user_key):
        """
        يقوم بمسح مجلد الـ Inbox للمستخدم، ويقرأ نتائج التنفيذ (نجاح/فشل)،
        ويقوم بتحديث ملف patterns.json ليتعلم النظام من النتائج، ثم يحذف الملف المقروء.
        """
        inbox_dir = os.path.join(self.pi_brain_dir, "users", user_key, "bridge", "inbox")
        memory_dir = os.path.join(self.pi_brain_dir, "users", user_key, "memory")
        patterns_path = os.path.join(memory_dir, "patterns.json")
        
        os.makedirs(inbox_dir, exist_ok=True)
        os.makedirs(memory_dir, exist_ok=True)

        # Load existing patterns
        patterns_data = []
        if os.path.exists(patterns_path):
            try:
                with open(patterns_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        patterns_data = data
                    elif isinstance(data, dict) and "lessons" in data:
                        patterns_data = data["lessons"]
            except Exception as e:
                logger.error(f"Error reading patterns {patterns_path}: {e}")

        # Scan Inbox
        new_lessons = 0
        for filename in os.listdir(inbox_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(inbox_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        result_data = json.load(f)
                    
                    status = result_data.get("status", "unknown")
                    manifest_id = result_data.get("manifest_id", "unknown")
                    
                    lesson = {
                        "timestamp": result_data.get("executed_at", "unknown"),
                        "manifest_id": manifest_id,
                        "status": status,
                    }
                    
                    if status == "success":
                        lesson["observation"] = f"Manifest {manifest_id} executed successfully. The schema and payload format were correct."
                    else:
                        error_msg = result_data.get("error", "Unknown error")
                        lesson["observation"] = f"Manifest {manifest_id} failed. Error: {error_msg}. Avoid this payload structure or ensure conditions are met."
                        
                    patterns_data.append(lesson)
                    new_lessons += 1
                    
                    # Remove the file after processing
                    os.remove(file_path)
                    logger.info(f"Processed and learned from inbox file: {filename}")
                    
                except Exception as e:
                    logger.error(f"Error processing inbox file {filename}: {e}")

        # Save back to patterns.json if we learned something new
        if new_lessons > 0:
            # Keep only the last 50 lessons to avoid bloating context
            if len(patterns_data) > 50:
                patterns_data = patterns_data[-50:]
                
            try:
                with open(patterns_path, "w", encoding="utf-8") as f:
                    json.dump({"lessons": patterns_data}, f, ensure_ascii=False, indent=2)
                logger.info(f"Updated patterns.json with {new_lessons} new lessons for {user_key}.")
            except Exception as e:
                logger.error(f"Error saving patterns {patterns_path}: {e}")
        
        return new_lessons

# للتجربة السريعة (Testing)
if __name__ == "__main__":
    engine = KnowledgeEngine()
    print("=== Testing System Rules Extraction ===")
    rules = engine.read_system_rules()
    print(f"Loaded rules length: {len(rules)} characters.")
    
    print("\n=== Testing Action Schema ===")
    print(engine.get_action_schema("create_invoice"))
