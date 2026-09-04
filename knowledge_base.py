import os
import sqlite3
import mailbox
import email
import re
import logging
from datetime import datetime
import uuid

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge.db")
MBOX_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "All mail Including Spam.mbox")

class KnowledgeBase:
    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()
        # Messages Table (Legacy/Email Archive)
        cur.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, subject TEXT, from_email TEXT, to_email TEXT, date TEXT, body TEXT)")
        cur.execute("CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(subject, body)")
        
        # Trips Table (From Airtable)
        cur.execute("CREATE TABLE IF NOT EXISTS trips (id TEXT PRIMARY KEY, title TEXT, description TEXT, itinerary TEXT, faqs TEXT)")
        cur.execute("CREATE VIRTUAL TABLE IF NOT EXISTS trips_fts USING fts5(title, description, itinerary, faqs)")

        # Documents Table (Uploaded files and manual entries)
        cur.execute("CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, filename TEXT, department TEXT, content TEXT, upload_date TEXT)")
        cur.execute("CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(filename, department, content)")

        # Strict Q/A Rules (Exact question -> exact answer without AI drafting)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS strict_qa_rules (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                normalized_question TEXT NOT NULL,
                answer TEXT NOT NULL,
                department TEXT NOT NULL,
                match_type TEXT NOT NULL DEFAULT 'normalized_exact',
                is_enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_strict_qa_rules_lookup ON strict_qa_rules(normalized_question, department, is_enabled)"
        )

        self.conn.commit()
        self._ensure_documents_fts_schema()
        self._ensure_company_id_columns()

    def _ensure_company_id_columns(self):
        cur = self.conn.cursor()
        for table in ("documents", "strict_qa_rules"):
            try:
                columns = [row[1] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()]
            except Exception:
                columns = []
            if "company_id" in columns:
                continue
            try:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN company_id TEXT DEFAULT 'fts'")
                cur.execute(f"UPDATE {table} SET company_id = 'fts' WHERE company_id IS NULL OR TRIM(company_id) = ''")
                self.conn.commit()
            except Exception as e:
                self.conn.rollback()
                logging.error(f"Failed to add company_id to {table}: {e}")

    def _company_id(self, company_id=None):
        cid = str(company_id or "").strip()
        return cid or "fts"

    def _ensure_documents_fts_schema(self):
        cur = self.conn.cursor()
        try:
            columns = [row[1] for row in cur.execute("PRAGMA table_info(documents_fts)").fetchall()]
        except Exception:
            columns = []

        expected = ["filename", "department", "content"]
        if columns == expected:
            return

        try:
            cur.execute("DROP TABLE IF EXISTS documents_fts")
            cur.execute("CREATE VIRTUAL TABLE documents_fts USING fts5(filename, department, content)")
            self._rebuild_documents_fts_index(commit=False)
            self.conn.commit()
            logging.info("Rebuilt documents_fts with schema filename, department, content")
        except Exception as e:
            self.conn.rollback()
            logging.error(f"Failed to ensure documents_fts schema: {e}")

    def _rebuild_documents_fts_index(self, commit=True):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM documents_fts")
        cur.execute(
            "INSERT INTO documents_fts(filename, department, content) SELECT filename, department, content FROM documents"
        )
        if commit:
            self.conn.commit()

    def _normalize_text(self, s):
        if not s:
            return ""
        s = re.sub(r"\s+", " ", str(s))
        return s.strip()

    def _normalize_document_content(self, content):
        text = str(content or "").replace("\r\n", "\n").replace("\r", "\n")
        if not text.strip():
            return ""

        normalized_lines = []
        blank_streak = 0
        for raw_line in text.split("\n"):
            line = re.sub(r"[ \t]+", " ", raw_line).strip()
            if not line:
                blank_streak += 1
                if blank_streak <= 1:
                    normalized_lines.append("")
                continue
            blank_streak = 0
            normalized_lines.append(line)

        return "\n".join(normalized_lines).strip()

    def _split_markdown_sections(self, content):
        text = str(content or "").replace("\r\n", "\n")
        if not text.strip():
            return []
        lines = text.split("\n")
        heading_indices = [
            idx for idx, line in enumerate(lines)
            if re.match(r"^\s*##\s+.+", line or "")
        ]
        if not heading_indices:
            return []

        sections = []
        for i, start_idx in enumerate(heading_indices):
            end_idx = heading_indices[i + 1] if i + 1 < len(heading_indices) else len(lines)
            heading = lines[start_idx].strip()
            body = "\n".join(lines[start_idx + 1:end_idx]).strip()
            block = heading if not body else f"{heading}\n\n{body}"
            sections.append({
                "heading": heading,
                "body": body,
                "block": block.strip(),
            })
        return sections

    def _split_markdown_blocks(self, content):
        text = str(content or "").replace("\r\n", "\n")
        if not text.strip():
            return []
        lines = text.split("\n")
        heading_indices = [
            idx for idx, line in enumerate(lines)
            if re.match(r"^\s*#{2,4}\s+.+", line or "")
        ]
        if not heading_indices:
            return []

        blocks = []
        for i, start_idx in enumerate(heading_indices):
            end_idx = heading_indices[i + 1] if i + 1 < len(heading_indices) else len(lines)
            heading = lines[start_idx].strip()
            body = "\n".join(lines[start_idx + 1:end_idx]).strip()
            block = heading if not body else f"{heading}\n\n{body}"
            blocks.append(
                {
                    "heading": heading,
                    "body": body,
                    "block": block.strip(),
                }
            )
        return blocks

    def _extract_markdown_sections(self, content, heading_keywords, max_chars=4000):
        text = str(content or "").strip()
        if not text:
            return ""

        sections = self._split_markdown_sections(text)
        if not sections:
            return text[:max_chars]

        normalized_keywords = [
            str(keyword or "").strip().lower()
            for keyword in (heading_keywords or [])
            if str(keyword or "").strip()
        ]

        selected_blocks = []
        seen = set()
        for section in sections:
            heading_lower = str(section.get("heading") or "").lower()
            if normalized_keywords and not any(keyword in heading_lower for keyword in normalized_keywords):
                continue
            block = str(section.get("block") or "").strip()
            if not block or block in seen:
                continue
            selected_blocks.append(block)
            seen.add(block)

        if not selected_blocks:
            return text[:max_chars]

        combined = "\n\n---\n\n".join(selected_blocks).strip()
        return combined[:max_chars]

    def _extract_relevant_document_block(self, filename, content, query_text, max_chars=900):
        text = self._normalize_document_content(content)
        if not text:
            return f"Document: {filename}"

        sections = self._split_markdown_blocks(text) or self._split_markdown_sections(text)
        normalized_query = self._normalize_rule_text(query_text)
        tokens = [
            token for token in re.findall(r"\w+", normalized_query, flags=re.UNICODE)
            if len(token) > 1 and token not in {"or", "and"}
        ]

        best_block = ""
        best_score = 0
        for section in sections:
            heading = str(section.get("heading") or "")
            body = str(section.get("body") or "")
            heading_norm = self._normalize_rule_text(heading)
            block_norm = self._normalize_rule_text(f"{heading}\n{body}")
            score = 0
            if normalized_query and normalized_query in block_norm:
                score += 10
            for token in tokens:
                if token in heading_norm:
                    score += 4
                score += block_norm.count(token)
            if score > best_score:
                best_score = score
                best_block = str(section.get("block") or "").strip()

        if best_score > 0 and best_block:
            return f"Document: {filename}\n{best_block[:max_chars]}..."

        return f"Document: {filename}\n{text[:max_chars]}..."

    def _normalize_rule_text(self, s):
        if not s:
            return ""
        s = str(s).strip().lower()
        # Remove Arabic diacritics and tatweel so equivalent customer messages match reliably.
        s = re.sub(r"[\u0610-\u061A\u0640\u064B-\u065F\u0670\u06D6-\u06ED]", "", s)
        s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
        s = re.sub(r"\s+", " ", s, flags=re.UNICODE)
        return s.strip()

    def _expand_departments(self, department):
        if not department:
            return []
        if isinstance(department, (list, tuple, set)):
            raw_values = department
        else:
            raw_values = str(department).split(",")
        depts = []
        seen = set()
        for value in raw_values:
            cleaned = self._normalize_text(value)
            if not cleaned:
                continue
            key = cleaned.lower()
            if key in seen:
                continue
            depts.append(cleaned)
            seen.add(key)
        return depts

    def _get_latest_documents_by_prefixes(self, department, filename_prefixes, limit_per_prefix=1):
        cur = self.conn.cursor()
        collected = []
        seen_ids = set()
        dept = self._normalize_text(department)
        for prefix in filename_prefixes or []:
            normalized_prefix = self._normalize_text(prefix)
            if not normalized_prefix:
                continue
            try:
                cur.execute(
                    """
                    SELECT id, filename, department, content, upload_date
                    FROM documents
                    WHERE lower(department) = lower(?) AND filename LIKE ?
                    ORDER BY upload_date DESC
                    LIMIT ?
                    """,
                    (dept, f"{normalized_prefix}%", limit_per_prefix)
                )
                for row in cur.fetchall():
                    if row[0] in seen_ids:
                        continue
                    collected.append(
                        {
                            "id": row[0],
                            "filename": row[1],
                            "department": row[2],
                            "content": row[3],
                            "upload_date": row[4],
                        }
                    )
                    seen_ids.add(row[0])
            except Exception:
                continue
        return collected

    def _extract_body(self, msg):
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype == "text/plain":
                    try:
                        return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
                    except Exception:
                        continue
                if ctype == "text/html":
                    try:
                        html = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
                        text = re.sub(r"<[^>]+>", " ", html)
                        return text
                    except Exception:
                        continue
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload is None:
                    payload = msg.get_payload()
                    if isinstance(payload, str):
                        return payload
                    return ""
                return payload.decode(msg.get_content_charset() or "utf-8", errors="ignore")
            except Exception:
                return ""
        return ""

    def build_from_mbox(self, mbox_path=MBOX_FILE, limit=None):
        if not os.path.exists(mbox_path):
            return False
        mbox = mailbox.mbox(mbox_path)
        cur = self.conn.cursor()
        count = 0
        for i, msg in enumerate(mbox):
            if limit and i >= limit:
                break
            try:
                subject = self._normalize_text(msg.get("Subject", ""))
                from_email = self._normalize_text(msg.get("From", ""))
                to_email = self._normalize_text(msg.get("To", ""))
                date_raw = msg.get("Date", "")
                date_val = ""
                try:
                    date_val = email.utils.parsedate_to_datetime(date_raw).isoformat()
                except Exception:
                    date_val = date_raw
                body = self._normalize_text(self._extract_body(msg))
                if not body and not subject:
                    continue
                cur.execute("INSERT INTO messages(subject, from_email, to_email, date, body) VALUES(?,?,?,?,?)", (subject, from_email, to_email, date_val, body))
                cur.execute("INSERT INTO messages_fts(subject, body) VALUES(?,?)", (subject, body))
                count += 1
            except Exception:
                continue
        self.conn.commit()
        return True

    def sync_trips_from_airtable(self, airtable_records):
        """
        Syncs trip data from Airtable to the local SQLite FTS index.
        Expects a list of dicts (records).
        """
        logging.info(f"Syncing {len(airtable_records)} trips to Knowledge Base...")
        cur = self.conn.cursor()
        
        # Clear existing trips to ensure fresh data
        cur.execute("DELETE FROM trips")
        cur.execute("DELETE FROM trips_fts")
        
        for record in airtable_records:
            fields = record.get('fields', {})
            trip_id = record.get('id')
            title = self._normalize_text(fields.get('Title', ''))
            
            # Combine Description, Details, and Includes for richer context
            desc_parts = [self._normalize_text(fields.get('Trip_Description', ''))]
            
            highlights = self._normalize_text(fields.get('TripHighlights', ''))
            if highlights:
                desc_parts.append(f"Highlights: {highlights}")

            details = self._normalize_text(fields.get('TripDetails', ''))
            if details:
                desc_parts.append(f"Details: {details}")
                
            includes = self._normalize_text(fields.get('TripIncludes', ''))
            if includes:
                desc_parts.append(f"Includes: {includes}")
            
            description = "\n\n".join(filter(None, desc_parts))

            # Correctly map ItinerarySteps
            itinerary = self._normalize_text(fields.get('ItinerarySteps', ''))
            
            # Extract FAQs if available (might be a list of IDs or strings, simplified here)
            faqs_raw = fields.get('TripFAQs', '')
            if isinstance(faqs_raw, list):
                faqs = "\n".join([str(f) for f in faqs_raw])
            else:
                faqs = str(faqs_raw)
            
            if not title:
                continue
                
            try:
                cur.execute("INSERT INTO trips (id, title, description, itinerary, faqs) VALUES (?, ?, ?, ?, ?)", 
                            (trip_id, title, description, itinerary, faqs))
                cur.execute("INSERT INTO trips_fts (title, description, itinerary, faqs) VALUES (?, ?, ?, ?)", 
                            (title, description, itinerary, faqs))
            except Exception as e:
                logging.error(f"Error indexing trip {trip_id}: {e}")
                
        self.conn.commit()
        logging.info("Trips sync completed.")

    def is_populated(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(1) FROM messages")
        msg_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(1) FROM trips")
        trip_count = cur.fetchone()[0]
        return msg_count > 0 or trip_count > 0

    def _sanitize_for_fts(self, query):
        """
        Sanitize query for FTS5 to prevent syntax errors.
        Removes special characters that FTS5 interprets as operators.
        """
        if not query:
            return ""
        # Remove characters that cause syntax errors in FTS5 standard query
        # We keep alphanumeric and spaces.
        # . : " * ^ - are special in FTS5.
        # Simplest approach: Replace non-alphanumeric with space, 
        # except maybe we want to keep some simple punctuation?
        # Let's just strip anything that isn't alphanumeric or space for safety.
        # Or better, wrap in quotes? Wrapping in quotes ("query") treats it as a phrase, 
        # but if user searches "Mrs." with quotes, it might still fail if "." is special inside?
        # No, "Mrs." as a phrase is fine.
        # But if the user query has unbalanced quotes, it breaks.
        
        # Strategy: Remove special chars: . " ' : * ^ - + ( ) [ ] { }
        # Keep only alphanumeric and spaces (and maybe @ for emails)
        cleaned = re.sub(r'[^\w\s@]', ' ', query)
        return self._normalize_text(cleaned)

    def search(self, query, top_k=3, department=None):
        """
        Searches Trips, Documents (KB), and Messages.
        Prioritizes Trips.
        If department is specified, only searches documents in that department.
        Uses a Fallback strategy: Strict -> Relaxed (Keywords).
        """
        # Sanitize raw query for FTS
        q = self._sanitize_for_fts(query)
        if not q:
            return []
            
        # Strategy 1: Strict Match (The whole sanitized query)
        results = self._perform_search(q, top_k, department, original_query=query)
        
        # Strategy 2: Relaxed Match (Keywords OR) if few results found
        if len(results) < 1:
            # Split into words, remove stop words / short words (< 4 chars)
            words = [w for w in q.split() if len(w) > 3]
            if words:
                # "OR" query in FTS5 syntax
                q_relaxed = " OR ".join(words)
                # logging.info(f"Fallback to relaxed search: {q_relaxed}")
                results.extend(self._perform_search(q_relaxed, top_k, department, original_query=query))
                 
        return results[:top_k] # Limit final results

    def _perform_search(self, fts_query, top_k, department=None, original_query=None):
        cur = self.conn.cursor()
        results = []
        dept_keys = [d.lower() for d in self._expand_departments(department)]
        is_religious_search = "religious" in dept_keys
        # 1. Search Trips
        if not is_religious_search:
            try:
                # FTS5 default ranking is bm25
                cur.execute("SELECT title, description, itinerary FROM trips_fts WHERE trips_fts MATCH ? ORDER BY rank LIMIT ?", (fts_query, top_k))
                trip_rows = cur.fetchall()
                for title, desc, itin in trip_rows:
                    content = f"Trip: {title}\nDescription: {desc[:300]}...\nItinerary: {itin[:300]}..."
                    results.append({"source": "Trip Database", "content": content, "score": 10}) 
            except Exception as e:
                # logging.error(f"Trip search error: {e}")
                pass

        # 2. Search Documents (Knowledge Base Uploads)
        try:
            if dept_keys:
                placeholders = ",".join("?" for _ in dept_keys)
                cur.execute(
                    f"""
                    SELECT filename, content, department
                    FROM documents_fts
                    WHERE documents_fts MATCH ?
                      AND lower(department) IN ({placeholders})
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (fts_query, *dept_keys, top_k),
                )
            else:
                cur.execute(
                    "SELECT filename, content, department FROM documents_fts WHERE documents_fts MATCH ? ORDER BY rank LIMIT ?",
                    (fts_query, top_k),
                )
            doc_rows = cur.fetchall()
            for filename, content, dept in doc_rows:
                snippet = self._extract_relevant_document_block(
                    filename,
                    content,
                    original_query or fts_query,
                    max_chars=900 if is_religious_search else 500,
                )
                results.append({"source": f"Knowledge Base ({dept})", "content": snippet, "score": 8})
        except Exception:
            pass

        # 3. Search Messages (Legacy)
        try:
            cur.execute("SELECT subject, body FROM messages_fts WHERE messages_fts MATCH ? ORDER BY rank LIMIT ?", (fts_query, top_k))
            msg_rows = cur.fetchall()
            for subject, body in msg_rows:
                results.append({"source": "Email Archive", "content": f"Subject: {subject}\nBody: {body[:300]}...", "score": 5})
        except Exception:
            pass
            
        return results

    def get_religious_core_context(self):
        """
        Returns core guidelines + safety rules context for the Religious department.
        This is ALWAYS injected by the AI agent when handling Religious queries.
        """
        ctx_parts = []

        managed_docs = self._get_latest_documents_by_prefixes(
            "Religious",
            [
                "1_Core_Guidelines_Hajj_Agent",
                "5_Safety_Rules_Handover",
            ],
        )
        for doc in managed_docs:
            content = self._normalize_document_content(doc.get("content"))
            if not content:
                continue
            label = "CORE AGENT GUIDELINES" if str(doc.get("filename", "")).startswith("1_") else "SAFETY RULES & HANDOVER"
            ctx_parts.append(f"===== {label} =====\n{content}")

        if not ctx_parts:
            cur = self.conn.cursor()
            core_keywords = [
                "تعليمات تشغيلية",
                "دور الـ ai agent",
                "أسلوب التواصل",
                "قاعدة cta",
                "مبدأ البيع",
                "اكتشاف احتياج",
                "قواعد الأهلية",
                "المطلوب للتسجيل",
                "الممنوعات",
                "تصنيف العملاء",
                "التعامل مع اعتراض السعر",
                "ملاحظات تشغيلية",
                "صيغة تحليل المحادثات",
                "أهم قاعدة",
            ]
            try:
                cur.execute(
                    "SELECT filename, content FROM documents WHERE department = 'Religious' AND (filename LIKE '%Core_Guidelines%' OR filename LIKE '%1_%' OR filename LIKE '%دليل%' OR filename LIKE '%Knowledge_Base%') ORDER BY upload_date DESC"
                )
                rows = cur.fetchall()
                for r in rows:
                    content = r[1] if len(r) > 1 else ""
                    extracted = self._extract_markdown_sections(content, core_keywords, max_chars=5000)
                    if extracted:
                        ctx_parts.append("===== CORE AGENT GUIDELINES =====\n" + extracted)
                        break
            except Exception:
                pass

        return "\n\n".join(ctx_parts)

    def get_hajj_programs_context(self):
        """
        Returns Hajj programs details context.
        Used by the AI agent for quick program reference.
        """
        ctx_parts = []

        managed_docs = self._get_latest_documents_by_prefixes(
            "Religious",
            [
                "3_Hajj_Programs_Details",
                "4_Hajj_Scenarios_Responses",
            ],
        )
        for doc in managed_docs:
            content = self._normalize_document_content(doc.get("content"))
            if not content:
                continue
            label = "HAJJ PROGRAMS DETAILS" if str(doc.get("filename", "")).startswith("3_") else "HAJJ SALES SCENARIOS"
            ctx_parts.append(f"===== {label} =====\n{content}")

        if not ctx_parts:
            cur = self.conn.cursor()
            program_keywords = [
                "ملخص البرامج السريع",
                "البرامج والأسعار الحالية",
                "تذاكر الطيران والعبارة",
                "قواعد الأهلية",
                "المطلوب للتسجيل",
                "ردود جاهزة حسب السيناريو",
            ]
            try:
                cur.execute(
                    "SELECT filename, content FROM documents WHERE department = 'Religious' AND (filename LIKE '%Hajj_Programs%' OR filename LIKE '%3_%' OR filename LIKE '%برامج%' OR filename LIKE '%تفاصيل%' OR filename LIKE '%Knowledge_Base%') ORDER BY upload_date DESC"
                )
                rows = cur.fetchall()
                for r in rows:
                    content = r[1] if len(r) > 1 else ""
                    extracted = self._extract_markdown_sections(content, program_keywords, max_chars=7000)
                    if extracted:
                        ctx_parts.append("===== HAJJ PROGRAMS DETAILS =====\n" + extracted)
                        break
            except Exception:
                pass

        return "\n\n".join(ctx_parts)

    def get_umrah_programs_context(self):
        """
        Returns Umrah programs details context for Religious sales replies.
        Prefers uploaded برامج_العمرة docs; falls back to FTS-like filename filters.
        """
        ctx_parts = []
        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                SELECT filename, content FROM documents
                WHERE department = 'Religious'
                  AND (
                    filename LIKE '%عمر%'
                    OR filename LIKE '%Umrah%'
                    OR filename LIKE '%umrah%'
                    OR content LIKE '%عمرة اقتصادي%'
                    OR content LIKE '%برامج_العمرة%'
                    OR content LIKE '%عمرة ٤ نجوم%'
                  )
                ORDER BY upload_date DESC
                LIMIT 6
                """
            )
            rows = cur.fetchall() or []
            seen = set()
            for filename, content in rows:
                key = str(filename or "").strip().lower()
                body = self._normalize_document_content(content)
                if not body or key in seen:
                    continue
                # Prefer docs that actually describe Umrah packages.
                if "عمرة" not in body and "umrah" not in body.lower():
                    continue
                seen.add(key)
                ctx_parts.append(f"===== UMRAH PROGRAMS DETAILS ({filename}) =====\n{body[:12000]}")
                if len(ctx_parts) >= 2:
                    break
        except Exception:
            pass
        return "\n\n".join(ctx_parts)

    def add_document(self, file_path, original_filename, department="general", company_id=None):
        """
        Add a file to the knowledge base. Reads text content from supported files (txt, pdf, etc.).
        Returns dict with status and document id.
        """
        doc_id = str(uuid.uuid4())
        content = ""
        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext == ".txt":
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            elif ext == ".pdf":
                # Try to extract text from PDF using PyMuPDF (fitz) if available
                try:
                    import fitz
                    doc_pdf = fitz.open(file_path)
                    for page in doc_pdf:
                        content += page.get_text()
                    doc_pdf.close()
                except ImportError:
                    try:
                        import pdfplumber
                        with pdfplumber.open(file_path) as pdf:
                            content = "\n".join(page.extract_text() or "" for page in pdf.pages)
                    except ImportError:
                        try:
                            import pdfminer
                            # Fallback: mark as binary file
                            content = f"[PDF file: {original_filename}]"
                        except ImportError:
                            content = f"[PDF file: {original_filename} - install PyMuPDF or pdfplumber for text extraction]"
            elif ext in (".docx", ".doc"):
                try:
                    import docx
                    doc = docx.Document(file_path)
                    content = "\n".join([p.text for p in doc.paragraphs])
                except ImportError:
                    content = f"[Document file: {original_filename}]"
            elif ext in (".xlsx", ".xls"):
                try:
                    import openpyxl
                    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
                    for sheet in wb.worksheets:
                        for row in sheet.iter_rows(values_only=True):
                            row_text = " ".join([str(c) for c in row if c is not None])
                            if row_text.strip():
                                content += row_text + "\n"
                    wb.close()
                except ImportError:
                    content = f"[Spreadsheet file: {original_filename}]"
            elif ext in (".csv",):
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            else:
                # Try to read as text anyway
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception:
                    content = f"[File: {original_filename} - binary format]"
        except Exception as e:
            logging.error(f"Error reading file {file_path}: {e}")
            content = f"[File: {original_filename} - could not be read]"

        content = self._normalize_document_content(content)
        now = datetime.now().isoformat()
        cid = self._company_id(company_id)

        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO documents (id, filename, department, content, upload_date, company_id) VALUES (?, ?, ?, ?, ?, ?)",
                (doc_id, original_filename, department, content, now, cid)
            )
            self._rebuild_documents_fts_index(commit=False)
            self.conn.commit()
            return {"status": "success", "document_id": doc_id, "message": f"Document '{original_filename}' added to {department}"}
        except Exception as e:
            self.conn.rollback()
            logging.error(f"Error adding document to DB: {e}")
            return {"status": "error", "message": str(e)}

    def add_text_document(self, filename, content, department="general", company_id=None):
        """
        Add a text document directly to the knowledge base (from manual input).
        Returns dict with status and document id.
        """
        doc_id = str(uuid.uuid4())
        content = self._normalize_document_content(content)
        now = datetime.now().isoformat()
        cid = self._company_id(company_id)

        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO documents (id, filename, department, content, upload_date, company_id) VALUES (?, ?, ?, ?, ?, ?)",
                (doc_id, filename, department, content, now, cid)
            )
            self._rebuild_documents_fts_index(commit=False)
            self.conn.commit()
            return {"status": "success", "document_id": doc_id, "message": f"Document '{filename}' created in {department}"}
        except Exception as e:
            self.conn.rollback()
            return {"status": "error", "message": str(e)}

    def get_documents(self, department=None, company_id=None):
        """
        Get documents filtered by department. 
        If department is None or 'All', returns all documents.
        Department can be a comma-separated list for multiple departments.
        """
        cur = self.conn.cursor()
        cid = self._company_id(company_id)
        company_clause = "COALESCE(NULLIF(company_id, ''), 'fts') = ?"
        if department and department.strip().lower() != 'all':
            depts = [d.strip() for d in department.split(",")]
            placeholders = ",".join(["?" for _ in depts])
            cur.execute(
                f"SELECT id, filename, department, upload_date, length(content) as content_size FROM documents WHERE department IN ({placeholders}) AND {company_clause} ORDER BY upload_date DESC",
                depts + [cid]
            )
        else:
            cur.execute(
                f"SELECT id, filename, department, upload_date, length(content) as content_size FROM documents WHERE {company_clause} ORDER BY upload_date DESC",
                (cid,)
            )

        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "filename": r[1],
                "department": r[2],
                "upload_date": r[3],
                "content_size": r[4]
            }
            for r in rows
        ]

    def get_document_info(self, doc_id):
        """
        Get full info of a document by ID.
        """
        cur = self.conn.cursor()
        cur.execute("SELECT id, filename, department, content, upload_date, company_id FROM documents WHERE id = ?", (doc_id,))
        row = cur.fetchone()
        if row:
            return {
                "id": row[0],
                "filename": row[1],
                "department": row[2],
                "content": row[3],
                "upload_date": row[4],
                "company_id": row[5] if len(row) > 5 else "fts",
            }
        return None

    def update_document(self, doc_id, filename=None, department=None, content=None):
        """
        Update a document's fields.
        """
        cur = self.conn.cursor()
        existing = self.get_document_info(doc_id)
        if not existing:
            return False

        new_filename = filename if filename is not None else existing["filename"]
        new_department = department if department is not None else existing["department"]
        new_content = content if content is not None else existing["content"]
        new_content = self._normalize_document_content(new_content)

        try:
            # Update documents table
            cur.execute(
                "UPDATE documents SET filename = ?, department = ?, content = ? WHERE id = ?",
                (new_filename, new_department, new_content, doc_id)
            )
            self._rebuild_documents_fts_index(commit=False)
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            logging.error(f"Error updating document {doc_id}: {e}")
            return False

    def delete_document(self, doc_id):
        """
        Delete a document by ID.
        """
        cur = self.conn.cursor()
        try:
            cur.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            self._rebuild_documents_fts_index(commit=False)
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            logging.error(f"Error deleting document {doc_id}: {e}")
            return False

    def add_strict_qa_rule(self, question, answer, department="general", match_type="normalized_exact", is_enabled=True, company_id=None):
        rule_id = str(uuid.uuid4())
        question = self._normalize_text(question)
        answer = self._normalize_text(answer)
        normalized_question = self._normalize_rule_text(question)
        department = self._normalize_text(department) or "general"
        match_type = self._normalize_text(match_type).lower() or "normalized_exact"
        now = datetime.now().isoformat()

        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO strict_qa_rules (
                    id, question, normalized_question, answer, department, match_type, is_enabled, created_at, updated_at, company_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (rule_id, question, normalized_question, answer, department, match_type, 1 if is_enabled else 0, now, now, self._company_id(company_id))
            )
            self.conn.commit()
            return {"status": "success", "rule_id": rule_id, "message": f"Strict Q/A rule created in {department}"}
        except Exception as e:
            self.conn.rollback()
            logging.error(f"Error creating strict Q/A rule: {e}")
            return {"status": "error", "message": str(e)}

    def get_strict_qa_rules(self, department=None, company_id=None):
        cur = self.conn.cursor()
        depts = self._expand_departments(department)
        cid = self._company_id(company_id)
        company_clause = "COALESCE(NULLIF(company_id, ''), 'fts') = ?"
        if depts and not any(d.lower() == "all" for d in depts):
            placeholders = ",".join(["?" for _ in depts])
            cur.execute(
                f"""
                SELECT id, question, answer, department, match_type, is_enabled, created_at, updated_at
                FROM strict_qa_rules
                WHERE department IN ({placeholders})
                  AND {company_clause}
                ORDER BY updated_at DESC
                """,
                depts + [cid]
            )
        else:
            cur.execute(
                f"""
                SELECT id, question, answer, department, match_type, is_enabled, created_at, updated_at
                FROM strict_qa_rules
                WHERE {company_clause}
                ORDER BY updated_at DESC
                """,
                (cid,)
            )

        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "question": r[1],
                "answer": r[2],
                "department": r[3],
                "match_type": r[4],
                "is_enabled": bool(r[5]),
                "created_at": r[6],
                "updated_at": r[7],
            }
            for r in rows
        ]

    def get_strict_qa_rule(self, rule_id):
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, question, answer, department, match_type, is_enabled, created_at, updated_at, company_id
            FROM strict_qa_rules
            WHERE id = ?
            """,
            (rule_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "question": row[1],
            "answer": row[2],
            "department": row[3],
            "match_type": row[4],
            "is_enabled": bool(row[5]),
            "created_at": row[6],
            "updated_at": row[7],
            "company_id": row[8] if len(row) > 8 else "fts",
        }

    def update_strict_qa_rule(self, rule_id, question=None, answer=None, department=None, match_type=None, is_enabled=None):
        existing = self.get_strict_qa_rule(rule_id)
        if not existing:
            return False

        new_question = self._normalize_text(question if question is not None else existing["question"])
        new_answer = self._normalize_text(answer if answer is not None else existing["answer"])
        new_department = self._normalize_text(department if department is not None else existing["department"]) or "general"
        new_match_type = self._normalize_text(match_type if match_type is not None else existing["match_type"]).lower() or "normalized_exact"
        new_is_enabled = existing["is_enabled"] if is_enabled is None else bool(is_enabled)
        normalized_question = self._normalize_rule_text(new_question)
        now = datetime.now().isoformat()

        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                UPDATE strict_qa_rules
                SET question = ?, normalized_question = ?, answer = ?, department = ?, match_type = ?, is_enabled = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_question, normalized_question, new_answer, new_department, new_match_type, 1 if new_is_enabled else 0, now, rule_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            logging.error(f"Error updating strict Q/A rule {rule_id}: {e}")
            return False

    def delete_strict_qa_rule(self, rule_id):
        cur = self.conn.cursor()
        try:
            cur.execute("DELETE FROM strict_qa_rules WHERE id = ?", (rule_id,))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            logging.error(f"Error deleting strict Q/A rule {rule_id}: {e}")
            return False

    def find_strict_qa_match(self, customer_message, department=None, company_id=None):
        normalized_message = self._normalize_rule_text(customer_message)
        if not normalized_message:
            return None

        departments = self._expand_departments(department)
        search_depts = []
        for dept in departments:
            if dept.lower() == "all":
                continue
            if dept not in search_depts:
                search_depts.append(dept)
        if not any(d.lower() == "general" for d in search_depts):
            search_depts.append("general")
        if not search_depts:
            search_depts = ["general"]

        placeholders = ",".join(["?" for _ in search_depts])
        cur = self.conn.cursor()

        cur.execute(
            f"""
            SELECT id, question, answer, department, match_type
            FROM strict_qa_rules
            WHERE is_enabled = 1
              AND match_type = 'normalized_exact'
              AND normalized_question = ?
              AND department IN ({placeholders})
              AND COALESCE(NULLIF(company_id, ''), 'fts') = ?
            ORDER BY CASE
                WHEN lower(department) = lower(?) THEN 0
                WHEN lower(department) = 'general' THEN 1
                ELSE 2
            END, updated_at DESC
            LIMIT 1
            """,
            [normalized_message, *search_depts, self._company_id(company_id), search_depts[0]],
        )
        row = cur.fetchone()
        if row:
            return {
                "id": row[0],
                "question": row[1],
                "answer": row[2],
                "department": row[3],
                "match_type": row[4],
                "matched_message": customer_message,
            }

        cur.execute(
            f"""
            SELECT id, question, normalized_question, answer, department, match_type
            FROM strict_qa_rules
            WHERE is_enabled = 1
              AND match_type = 'contains'
              AND department IN ({placeholders})
              AND COALESCE(NULLIF(company_id, ''), 'fts') = ?
            ORDER BY CASE
                WHEN lower(department) = lower(?) THEN 0
                WHEN lower(department) = 'general' THEN 1
                ELSE 2
            END, updated_at DESC
            """,
            [*search_depts, self._company_id(company_id), search_depts[0]],
        )
        for row in cur.fetchall():
            if row[2] and row[2] in normalized_message:
                return {
                    "id": row[0],
                    "question": row[1],
                    "answer": row[3],
                    "department": row[4],
                    "match_type": row[5],
                    "matched_message": customer_message,
                }
        return None

    def build_if_needed(self, mbox_path=MBOX_FILE):
        if not self.is_populated():
            self.build_from_mbox(mbox_path)
        return True
