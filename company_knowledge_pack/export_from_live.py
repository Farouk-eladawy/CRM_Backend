# -*- coding: utf-8 -*-
"""Copy what the live agent actually reads into this editable folder.

Reads the knowledge database beside the project, plus the catalog files
and learned corrections. Does not copy config, tokens, or the 3 GB database file.
"""
import json
import os
import shutil
import sqlite3
from datetime import datetime

PACK_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(PACK_DIR)


def _safe_filename(name, used):
    cleaned = str(name or "document.md").strip()
    for char in '<>:"/\\|?*':
        cleaned = cleaned.replace(char, "_")
    cleaned = cleaned.rstrip(". ") or "document.md"
    if not cleaned.lower().endswith(".md"):
        cleaned += ".md"
    candidate = cleaned
    index = 2
    while candidate.lower() in used:
        stem, ext = os.path.splitext(cleaned)
        candidate = f"{stem}_{index}{ext}"
        index += 1
    used.add(candidate.lower())
    return candidate


def _write_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def export_documents(conn):
    docs_dir = os.path.join(PACK_DIR, "documents")
    os.makedirs(docs_dir, exist_ok=True)
    for name in os.listdir(docs_dir):
        if name.lower().endswith(".md"):
            os.remove(os.path.join(docs_dir, name))
    used = set()
    rows = conn.execute(
        "SELECT filename, department, content FROM documents ORDER BY department, filename"
    ).fetchall()
    written = []
    for filename, department, content in rows:
        target_name = _safe_filename(filename, used)
        header = (
            f"<!-- department: {department or 'General'} -->\n"
            f"<!-- filename: {filename or target_name} -->\n\n"
        )
        with open(os.path.join(docs_dir, target_name), "w", encoding="utf-8") as handle:
            handle.write(header + (content or ""))
        written.append({"file": target_name, "department": department or "General", "chars": len(content or "")})
    return written


def export_trips(conn):
    rows = conn.execute("SELECT id, title, description, itinerary, faqs FROM trips ORDER BY title").fetchall()
    trips = [
        {"id": row[0], "title": row[1] or "", "description": row[2] or "", "itinerary": row[3] or "", "faqs": row[4] or ""}
        for row in rows
    ]
    _write_json(os.path.join(PACK_DIR, "trips.json"), trips)
    return len(trips)


def export_rules(conn):
    rows = conn.execute(
        "SELECT question, answer, department, match_type, is_enabled FROM strict_qa_rules ORDER BY department, question"
    ).fetchall()
    rules = [
        {
            "question": row[0] or "",
            "answer": row[1] or "",
            "department": row[2] or "General",
            "match_type": row[3] or "normalized_exact",
            "is_enabled": bool(row[4]),
        }
        for row in rows
    ]
    _write_json(os.path.join(PACK_DIR, "strict_qa.json"), rules)
    return len(rules)


def copy_side_files():
    copied = []
    corrections = os.path.join(PROJECT_DIR, "learned_corrections.json")
    if os.path.exists(corrections):
        shutil.copy2(corrections, os.path.join(PACK_DIR, "learned_corrections.json"))
        copied.append("learned_corrections.json")
    catalogs = os.path.join(PACK_DIR, "catalogs")
    os.makedirs(catalogs, exist_ok=True)
    for name in ("Get_Your_Guide_data.json", "Viator_data.json", "Headout_data.json"):
        source = os.path.join(PROJECT_DIR, name)
        if os.path.exists(source):
            shutil.copy2(source, os.path.join(catalogs, name))
            copied.append(f"catalogs/{name}")
    return copied


def main():
    db_path = os.path.join(PROJECT_DIR, "knowledge.db")
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    documents = export_documents(conn)
    trip_count = export_trips(conn)
    rule_count = export_rules(conn)
    conn.close()
    copied = copy_side_files()
    manifest = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "documents": len(documents),
        "trips": trip_count,
        "strict_qa": rule_count,
        "files": copied,
        "document_files": documents,
    }
    _write_json(os.path.join(PACK_DIR, "manifest.json"), manifest)
    print(f"documents={len(documents)} trips={trip_count} strict_qa={rule_count}")
    print("copied=" + ", ".join(copied))


if __name__ == "__main__":
    main()
