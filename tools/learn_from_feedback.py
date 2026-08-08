import sys
import json
import os
import difflib
from datetime import datetime

# Path to the learning database
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'learning_db.json')

def load_db():
    if not os.path.exists(DB_PATH):
        return {"lessons": [], "stats": {"approved": 0, "corrected": 0}}
    try:
        with open(DB_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"lessons": [], "stats": {"approved": 0, "corrected": 0}}

def save_db(data):
    with open(DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def learn(original_ai_draft, final_human_text, context=""):
    """
    Compares AI draft with Human final text.
    If different, records a lesson.
    """
    db = load_db()
    
    # Clean strings
    original = str(original_ai_draft).strip()
    final = str(final_human_text).strip()
    
    # 1. Exact Match (Approval)
    if original == final:
        print("✅ Perfect Match! No learning needed. (Reinforcement)")
        db["stats"]["approved"] += 1
        save_db(db)
        return

    # 2. Difference Detected (Correction)
    print("⚠️ Correction Detected! Learning from human edit...")
    
    # Calculate similarity ratio
    matcher = difflib.SequenceMatcher(None, original, final)
    ratio = matcher.ratio()
    
    # Generate diff report
    diff = list(difflib.ndiff(original.splitlines(), final.splitlines()))
    
    lesson = {
        "timestamp": datetime.now().isoformat(),
        "context": context, # e.g., "Customer asked for price"
        "ai_draft": original,
        "human_final": final,
        "similarity": round(ratio * 100, 2),
        "diff_summary": [line for line in diff if line.startswith('- ') or line.startswith('+ ')]
    }
    
    db["lessons"].append(lesson)
    db["stats"]["corrected"] += 1
    
    # Keep only last 100 lessons to avoid file bloat
    if len(db["lessons"]) > 100:
        db["lessons"] = db["lessons"][-100:]
        
    save_db(db)
    print(f"📚 Lesson Saved! Similarity: {lesson['similarity']}%")

if __name__ == "__main__":
    # Usage: python learn_from_feedback.py "AI said this" "Human changed to this" "Context"
    if len(sys.argv) < 3:
        print("Usage: python learn_from_feedback.py <ai_draft> <human_final> [context]")
    else:
        ai_text = sys.argv[1]
        human_text = sys.argv[2]
        ctx = sys.argv[3] if len(sys.argv) > 3 else "General"
        learn(ai_text, human_text, ctx)
