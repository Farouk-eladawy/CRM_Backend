# -*- coding: utf-8 -*-
"""Build n8n/knowledge_bundle.json from the editable pack files."""
import json
import os

PACK_DIR = os.path.dirname(os.path.abspath(__file__))


def read_text(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def parse_document(name, text):
    department = "General"
    filename = name
    lines = text.splitlines()
    start = 0
    for index, line in enumerate(lines[:6]):
        stripped = line.strip()
        if stripped.startswith("<!-- department:"):
            department = stripped[len("<!-- department:"):].rstrip("-> ").strip() or department
            start = index + 1
        elif stripped.startswith("<!-- filename:"):
            filename = stripped[len("<!-- filename:"):].rstrip("-> ").strip() or filename
            start = index + 1
        elif stripped == "":
            continue
        else:
            break
    return {
        "filename": filename,
        "department": department,
        "content": "\n".join(lines[start:]).strip(),
    }


def main():
    company = json.loads(read_text(os.path.join(PACK_DIR, "company.json")))
    documents = []
    docs_dir = os.path.join(PACK_DIR, "documents")
    for name in sorted(os.listdir(docs_dir)):
        if name.lower().endswith(".md"):
            documents.append(parse_document(name, read_text(os.path.join(docs_dir, name))))
    trips = []
    for trip in json.loads(read_text(os.path.join(PACK_DIR, "trips.json"))):
        trips.append({
            "title": trip.get("title") or "",
            "description": str(trip.get("description") or "")[:600],
            "faqs": str(trip.get("faqs") or "")[:400],
        })
    rules = json.loads(read_text(os.path.join(PACK_DIR, "strict_qa.json")))
    ads = json.loads(read_text(os.path.join(PACK_DIR, "facebook_ad_products.json")))
    corrections_path = os.path.join(PACK_DIR, "learned_corrections.json")
    corrections = json.loads(read_text(corrections_path)) if os.path.exists(corrections_path) else []
    bundle = {
        "company": company,
        "reply_rules": read_text(os.path.join(PACK_DIR, "reply_rules.md")),
        "documents": documents,
        "trips": trips,
        "strict_qa": rules,
        "facebook_ads": ads.get("ads") or {},
        "learned_corrections": corrections[-30:],
    }
    out_dir = os.path.join(PACK_DIR, "n8n")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "knowledge_bundle.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(bundle, handle, ensure_ascii=False)
    print(f"Wrote {out_path} bytes={os.path.getsize(out_path)} docs={len(documents)} trips={len(trips)} qa={len(rules)}")


if __name__ == "__main__":
    main()
