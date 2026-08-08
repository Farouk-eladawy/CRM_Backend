import json
import os
import re
import sys
from collections import OrderedDict
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from knowledge_base import KnowledgeBase


MASTER_FILE = os.path.join(BASE_DIR, "FTS_Hajj_Sales_Knowledge_Base_Final.md")
OUTPUT_DIR = os.path.join(BASE_DIR, "knowledge_sources", "religious")
BACKUP_DIR = os.path.join(BASE_DIR, "migration_backups")
DEPARTMENT = "Religious"

DOC_LAYOUT = OrderedDict(
    [
        (
            "1_Core_Guidelines_Hajj_Agent.md",
            {
                "title": "# Core Guidelines - Hajj Agent",
                "intro": "> تعليمات التشغيل الأساسية ونبرة الرد وCTA واكتشاف الاحتياج.",
                "sections": [
                    "## 0. تعليمات تشغيلية للنظام",
                    "## 1. دور الـ AI Agent",
                    "## 3. أسلوب التواصل الإلزامي",
                    "## 4. قاعدة CTA النهائية",
                    "## 5. مبدأ البيع: بيع النتيجة وليس المواصفة",
                    "## 6. اكتشاف احتياج العميل",
                ],
            },
        ),
        (
            "2_Company_Info_FTS_Hajj.md",
            {
                "title": "# Company Info - FTS Hajj",
                "intro": "> بيانات الشركة والعنوان وأرقام التواصل.",
                "sections": [
                    "## 2. بيانات الشركة",
                ],
            },
        ),
        (
            "3_Hajj_Programs_Details.md",
            {
                "title": "# Hajj Programs Details",
                "intro": "> البرامج والأسعار والأهلية والتسجيل الحالي.",
                "sections": [
                    "## 7. البرامج والأسعار الحالية",
                    "## 8. تذاكر الطيران والعبارة",
                    "## 9. قواعد الأهلية والتقديم",
                    "## 10. المطلوب للتسجيل الحالي",
                ],
            },
        ),
        (
            "4_Hajj_Scenarios_Responses.md",
            {
                "title": "# Hajj Scenarios Responses",
                "intro": "> ردود جاهزة حسب السيناريو واعتراضات السعر.",
                "sections": [
                    "## 13. ردود جاهزة حسب السيناريو",
                    "## 14. التعامل مع اعتراض السعر",
                ],
            },
        ),
        (
            "5_Safety_Rules_Handover.md",
            {
                "title": "# Safety Rules And Handover",
                "intro": "> الممنوعات، التصنيف، ملاحظات السيلز، وصيغة التحليل النهائي.",
                "sections": [
                    "## 11. الممنوعات",
                    "## 12. تصنيف العملاء",
                    "## 15. ملاحظات تشغيلية لفريق السيلز",
                    "## 16. صيغة تحليل المحادثات للـ AI Agent",
                    "## 17. أهم قاعدة نهائية",
                ],
            },
        ),
    ]
)


def split_top_level_sections(content):
    text = str(content or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    section_indices = [
        idx for idx, line in enumerate(lines)
        if re.match(r"^\s*##\s+.+", line or "")
    ]
    sections = OrderedDict()
    for i, start_idx in enumerate(section_indices):
        end_idx = section_indices[i + 1] if i + 1 < len(section_indices) else len(lines)
        heading = lines[start_idx].strip()
        block = "\n".join(lines[start_idx:end_idx]).strip()
        sections[heading] = block
    return sections


def build_documents(master_content):
    sections = split_top_level_sections(master_content)
    docs = OrderedDict()
    for filename, spec in DOC_LAYOUT.items():
        blocks = []
        for heading in spec["sections"]:
            block = sections.get(heading)
            if not block:
                raise ValueError(f"Missing required section in master KB: {heading}")
            blocks.append(block)
        parts = [spec["title"], "", spec["intro"]]
        for block in blocks:
            parts.extend(["", "---", "", block])
        docs[filename] = "\n".join(parts).strip() + "\n"
    return docs


def backup_existing_religious_docs(kb):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"religious_kb_split_backup_{ts}.json")
    docs = kb.get_documents(DEPARTMENT)
    payload = []
    for doc in docs:
        full = kb.get_document_info(doc["id"])
        if full:
            payload.append(full)
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return backup_path, payload


def sync_documents(kb, docs):
    existing = kb.get_documents(DEPARTMENT)
    for doc in existing:
        kb.delete_document(doc["id"])
    created = []
    for filename, content in docs.items():
        result = kb.add_text_document(filename, content, DEPARTMENT)
        if result.get("status") != "success":
            raise RuntimeError(f"Failed to add document {filename}: {result}")
        created.append({"filename": filename, "document_id": result.get("document_id")})
    return created


def write_split_files(docs):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    paths = []
    for filename, content in docs.items():
        path = os.path.join(OUTPUT_DIR, filename)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        paths.append(path)
    return paths


def main():
    if not os.path.exists(MASTER_FILE):
        raise FileNotFoundError(MASTER_FILE)

    with open(MASTER_FILE, "r", encoding="utf-8", errors="ignore") as f:
        master_content = f.read()

    docs = build_documents(master_content)
    file_paths = write_split_files(docs)

    kb = KnowledgeBase()
    backup_path, old_docs = backup_existing_religious_docs(kb)
    created = sync_documents(kb, docs)

    print(
        json.dumps(
            {
                "backup_path": backup_path,
                "old_religious_docs_count": len(old_docs),
                "new_religious_docs_count": len(created),
                "output_dir": OUTPUT_DIR,
                "files": file_paths,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
