# -*- coding: utf-8 -*-
"""Build a clean knowledge.db from this folder after you edit the files.

Default output is company_knowledge_pack/build/knowledge.db.
It does not replace the live CRM database.
"""
import argparse
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime

PACK_DIR = os.path.dirname(os.path.abspath(__file__))


def _read_text(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _parse_document(text):
    department = "General"
    filename = ""
    lines = text.splitlines()
    body_start = 0
    for index, line in enumerate(lines[:6]):
        stripped = line.strip()
        if stripped.startswith("<!-- department:"):
            department = stripped[len("<!-- department:"):].rstrip("-> ").strip()
            body_start = index + 1
        elif stripped.startswith("<!-- filename:"):
            filename = stripped[len("<!-- filename:"):].rstrip("-> ").strip()
            body_start = index + 1
        elif stripped == "":
            continue
        else:
            break
    body = "\n".join(lines[body_start:]).lstrip("\n")
    return department or "General", filename, body


def _init_db(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE messages (id INTEGER PRIMARY KEY, subject TEXT, from_email TEXT, to_email TEXT, date TEXT, body TEXT)")
    cur.execute("CREATE VIRTUAL TABLE messages_fts USING fts5(subject, body)")
    cur.execute("CREATE TABLE trips (id TEXT PRIMARY KEY, title TEXT, description TEXT, itinerary TEXT, faqs TEXT)")
    cur.execute("CREATE VIRTUAL TABLE trips_fts USING fts5(title, description, itinerary, faqs)")
    cur.execute("CREATE TABLE documents (id TEXT PRIMARY KEY, filename TEXT, department TEXT, content TEXT, upload_date TEXT, company_id TEXT)")
    cur.execute("CREATE VIRTUAL TABLE documents_fts USING fts5(filename, department, content)")
    cur.execute(
        """
        CREATE TABLE strict_qa_rules (
            id TEXT PRIMARY KEY,
            question TEXT NOT NULL,
            normalized_question TEXT NOT NULL,
            answer TEXT NOT NULL,
            department TEXT NOT NULL,
            match_type TEXT NOT NULL DEFAULT 'normalized_exact',
            is_enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            company_id TEXT
        )
        """
    )
    cur.execute("CREATE INDEX idx_strict_qa_rules_lookup ON strict_qa_rules(normalized_question, department, is_enabled)")
    conn.commit()
    return conn


def _normalize_question(text):
    value = str(text or "").strip().lower()
    value = re.sub(r"[\u0610-\u061A\u0640\u064B-\u065F\u0670\u06D6-\u06ED]", "", value)
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    value = re.sub(r"\s+", " ", value, flags=re.UNICODE)
    return value.strip()


def build(output_path, company_id):
    conn = _init_db(output_path)
    cur = conn.cursor()
    now = datetime.now().isoformat()
    doc_count = 0
    docs_dir = os.path.join(PACK_DIR, "documents")
    if os.path.isdir(docs_dir):
        for name in sorted(os.listdir(docs_dir)):
            if not name.lower().endswith(".md"):
                continue
            department, filename, content = _parse_document(_read_text(os.path.join(docs_dir, name)))
            filename = filename or name
            cur.execute(
                "INSERT INTO documents (id, filename, department, content, upload_date, company_id) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), filename, department, content, now, company_id),
            )
            doc_count += 1
    cur.execute("DELETE FROM documents_fts")
    cur.execute("INSERT INTO documents_fts(filename, department, content) SELECT filename, department, content FROM documents")

    trip_count = 0
    trips_path = os.path.join(PACK_DIR, "trips.json")
    if os.path.exists(trips_path):
        trips = json.loads(_read_text(trips_path) or "[]")
        for trip in trips:
            cur.execute(
                "INSERT INTO trips (id, title, description, itinerary, faqs) VALUES (?, ?, ?, ?, ?)",
                (
                    str(trip.get("id") or uuid.uuid4()),
                    trip.get("title") or "",
                    trip.get("description") or "",
                    trip.get("itinerary") or "",
                    trip.get("faqs") or "",
                ),
            )
            trip_count += 1
    cur.execute("DELETE FROM trips_fts")
    cur.execute("INSERT INTO trips_fts(title, description, itinerary, faqs) SELECT title, description, itinerary, faqs FROM trips")

    qa_count = 0
    qa_path = os.path.join(PACK_DIR, "strict_qa.json")
    if os.path.exists(qa_path):
        rules = json.loads(_read_text(qa_path) or "[]")
        for rule in rules:
            question = rule.get("question") or ""
            cur.execute(
                """
                INSERT INTO strict_qa_rules
                (id, question, normalized_question, answer, department, match_type, is_enabled, created_at, updated_at, company_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    question,
                    _normalize_question(question),
                    rule.get("answer") or "",
                    rule.get("department") or "General",
                    rule.get("match_type") or "normalized_exact",
                    1 if rule.get("is_enabled", True) else 0,
                    now,
                    now,
                    company_id,
                ),
            )
            qa_count += 1
    conn.commit()
    conn.close()
    return doc_count, trip_count, qa_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=os.path.join(PACK_DIR, "build", "knowledge.db"))
    parser.add_argument("--company-id", default="")
    args = parser.parse_args()
    company_id = args.company_id.strip()
    company_path = os.path.join(PACK_DIR, "company.json")
    if not company_id and os.path.exists(company_path):
        company_id = str(json.loads(_read_text(company_path)).get("company_id") or "").strip()
    company_id = company_id or "company"
    live = os.path.abspath(os.path.join(PACK_DIR, "..", "knowledge.db"))
    if os.path.abspath(args.output) == live:
        raise SystemExit("Refusing to overwrite the live knowledge.db. Choose another --output path.")
    docs, trips, rules = build(os.path.abspath(args.output), company_id)
    print(f"Wrote {os.path.abspath(args.output)}")
    print(f"documents={docs} trips={trips} strict_qa={rules} company_id={company_id}")


if __name__ == "__main__":
    main()
