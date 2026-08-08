import datetime as dt
import os
import json
import time
import glob
import logging
import threading
import requests
import uuid
from urllib.parse import quote
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
from runtime.pi_brain.knowledge_engine import KnowledgeEngine

logger = logging.getLogger(__name__)

#region debug-point capability-dev-str-get.dbg_emit
def _dbg_emit(event_name, payload=None, run_id="capability-dev"):
    try:
        url = str(os.environ.get("DEBUG_SERVER_URL") or "").strip()
        session_id = str(os.environ.get("DEBUG_SESSION_ID") or "").strip()
        if not url or not session_id:
            return
        safe_payload = payload if isinstance(payload, dict) else {"value": payload}
        body = {
            "sessionId": session_id,
            "runId": str(run_id or "capability-dev"),
            "hypothesisId": "capability-dev",
            "event": str(event_name or "event"),
            "payload": safe_payload,
        }
        requests.post(url, json=body, timeout=2)
    except Exception:
        return
#endregion debug-point capability-dev-str-get.dbg_emit


def _payload_preview(value, limit=1200):
    try:
        if isinstance(value, (dict, list)):
            text = json.dumps(value, ensure_ascii=False, default=str)
        else:
            text = str(value)
    except Exception:
        text = repr(value)
    text = text.replace("\n", "\\n")
    return text[:limit]

class BackgroundTaskEngine:
    """
    محرك المهام الخلفية (Background Task Engine)
    وظيفته:
    1. مراقبة الـ Outbox الخاص بـ PI لتنفيذ الـ Manifests التي أرسلها.
    2. مراقبة الـ Watchers للتأكد من تحقق الشروط (بالاتصال المباشر بـ Airtable).
    3. مراقبة الـ Scheduled Tasks لتنفيذ المهام في وقتها.
    4. إعادة نتائج التنفيذ إلى الـ Inbox الخاص بـ PI.
    """
    
    def __init__(self, pi_brain_dir="runtime/pi_brain", check_interval=60):
        self.pi_brain_dir = pi_brain_dir
        self.check_interval = check_interval
        self.is_running = False
        self.users_dir = os.path.join(self.pi_brain_dir, "users")
        self.config = self._load_config()
        self.airtable_config = self.config.get("airtable", {})
        self.knowledge_engine = KnowledgeEngine(pi_brain_dir=self.pi_brain_dir)

    def _load_config(self):
        """تحميل الإعدادات من ملف config.json الرئيسي"""
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}

    def _get_user_dirs(self):
        """إرجاع قائمة بمسارات المستخدمين المتاحة"""
        if not os.path.exists(self.users_dir):
            return []
        return [os.path.join(self.users_dir, d) for d in os.listdir(self.users_dir) if os.path.isdir(os.path.join(self.users_dir, d))]

    def _resolve_airtable_target(self, base_type="main", table_name=None, is_religious=None):
        base_type_normalized = str(base_type or "main").strip().lower()
        table_name = str(table_name or "").strip()
        religious_tables = {
            "حجاج حج مباشر", "حجاج حج مباشر باقات", "حجاج حج قرعة",
            "حجاج تحسين", "حجاج بري", "حجاج كوكتيل", "إحصائيات البرامج", "استفسارات جديدة"
        }
        if is_religious is None and table_name in religious_tables:
            is_religious = True
        if bool(is_religious):
            base_type_normalized = "religious"
        if base_type_normalized == "religious":
            base_id = self.airtable_config.get("religious_base_id")
            resolved_table_name = table_name or "استفسارات جديدة"
        elif base_type_normalized == "trips":
            base_id = self.airtable_config.get("trips_base_id")
            resolved_table_name = table_name or self.airtable_config.get("tables", {}).get("trips_catalog", "Trips")
        else:
            base_id = self.airtable_config.get("base_id")
            resolved_table_name = table_name or self.airtable_config.get("tables", {}).get("main_list", "List")
        return str(base_id or "").strip(), str(resolved_table_name or "").strip(), base_type_normalized

    def _normalize_airtable_update_fields(self, fields):
        fields = fields if isinstance(fields, dict) else {}
        try:
            from airtable_fields import ID_TO_READABLE_NAME
            exact_by_trimmed = {}
            exact_by_lower = {}
            for value in (ID_TO_READABLE_NAME or {}).values():
                if not isinstance(value, str):
                    continue
                exact_by_trimmed.setdefault(value.strip(), value)
                exact_by_lower.setdefault(value.strip().lower(), value)
            normalized = {}
            for key, value in fields.items():
                if isinstance(key, str):
                    trimmed = key.strip()
                    canonical = exact_by_trimmed.get(trimmed) or exact_by_lower.get(trimmed.lower()) or key
                else:
                    canonical = key
                normalized[canonical] = value
            return normalized
        except Exception:
            return fields

    def _coerce_airtable_update_fields(self, fields, field_types=None):
        fields = fields if isinstance(fields, dict) else {}
        field_types = field_types if isinstance(field_types, dict) else {}
        normalized_types = {}
        for key, value in field_types.items():
            if not isinstance(key, str):
                continue
            normalized_types[key] = str(value or "").strip()
            normalized_types[key.strip()] = str(value or "").strip()
            normalized_types[key.strip().lower()] = str(value or "").strip()
        coerced = {}
        for field_name, value in fields.items():
            field_key = str(field_name or "")
            field_type = (
                normalized_types.get(field_key)
                or normalized_types.get(field_key.strip())
                or normalized_types.get(field_key.strip().lower())
                or ""
            ).strip()
            if field_type == "multipleSelects":
                if isinstance(value, list):
                    coerced[field_name] = [str(item).strip() for item in value if str(item).strip()]
                else:
                    normalized_value = str(value or "").strip()
                    coerced[field_name] = [normalized_value] if normalized_value else []
            else:
                coerced[field_name] = value
        return coerced

    def _current_cairo_date_str(self, day_offset=0):
        try:
            if ZoneInfo is not None:
                now_cairo = dt.datetime.now(ZoneInfo("Africa/Cairo"))
            else:
                now_cairo = dt.datetime.utcnow() + dt.timedelta(hours=2)
        except Exception:
            now_cairo = dt.datetime.utcnow() + dt.timedelta(hours=2)
        target_date = (now_cairo + dt.timedelta(days=int(day_offset or 0))).date()
        return target_date.isoformat()

    def _resolve_record_date_value(self, fields, date_type):
        fields = fields if isinstance(fields, dict) else {}
        normalized_date_type = str(date_type or "").strip()
        if not normalized_date_type or not fields:
            return ""
        field_variations = [
            normalized_date_type,
            normalized_date_type.strip(),
            normalized_date_type.replace("Created Date", "Create Date"),
            normalized_date_type.replace("Created", "Create"),
            normalized_date_type.replace("ed ", "e "),
            normalized_date_type.replace("ed ", "e ").strip(),
        ]
        if normalized_date_type.lower() in {"create date", "created date"}:
            field_variations.extend(["Create Date", "Create Date  ", "Created Date"])
        elif normalized_date_type.lower() == "date trip":
            field_variations.extend(["Date Trip", "date trip"])
        for variant in field_variations:
            if variant in fields:
                return fields.get(variant) or ""
        normalized_target = normalized_date_type.lower()
        for key, value in fields.items():
            key_normalized = str(key or "").strip().lower()
            if key_normalized == normalized_target:
                return value or ""
        if "create" in normalized_target and "date" in normalized_target:
            for key, value in fields.items():
                key_normalized = str(key or "").lower()
                if "create" in key_normalized and "date" in key_normalized:
                    return value or ""
        return ""

    def _extract_date_only(self, value):
        value_str = str(value or "").strip()
        if not value_str:
            return ""
        try:
            iso_value = value_str.replace("Z", "+00:00")
            parsed = dt.datetime.fromisoformat(iso_value)
            if parsed.tzinfo is not None:
                if ZoneInfo is not None:
                    parsed = parsed.astimezone(ZoneInfo("Africa/Cairo"))
                else:
                    parsed = parsed + dt.timedelta(hours=2)
            return parsed.date().isoformat()
        except Exception:
            return value_str[:10]

    def _resolve_query_date_field_name(self, date_type):
        normalized = str(date_type or "").strip().lower()
        if normalized in {"create date", "created date"}:
            return "Create Date  "
        if normalized == "date trip":
            return "Date Trip"
        return str(date_type or "").strip()

    def _fetch_airtable_records_paginated(self, url, headers, params=None):
        params = dict(params or {})
        all_records = []
        offset = None
        while True:
            current_params = dict(params)
            if offset:
                current_params["offset"] = offset
            response = requests.get(url, headers=headers, params=current_params, timeout=30)
            response.raise_for_status()
            data = response.json()
            all_records.extend(data.get("records", []) or [])
            offset = data.get("offset")
            if not offset:
                break
        return all_records

    def _send_whatsapp_notification(self, phone, text):
        """إرسال رسالة واتساب فعلية للمستخدم (Admin) باستخدام Evolution API
           تم تخصيص هذا الإرسال ليكون عبر Instance خاصة بالإشعارات الداخلية فقط
           ولن يؤثر على رسائل العملاء في النظام الأساسي.
        """
        instance_name = "fts_internal_notifications"
        base_url = "http://localhost:8080"
        api_key = "429683C4C977415CAAFCCE10F7D57E11"
        try:
            import chat_db
            raw = chat_db.get_setting("internal_whatsapp_notifications_config")
            cfg = raw
            if isinstance(cfg, str) and cfg.strip():
                try:
                    cfg = json.loads(cfg)
                except Exception:
                    cfg = {}
            if isinstance(cfg, dict):
                instance_name = str(cfg.get("instanceName") or instance_name).strip() or instance_name
                base_url = str(cfg.get("providerBaseUrl") or base_url).strip().rstrip("/") or base_url
                api_key = str(cfg.get("apiKey") or api_key).strip() or api_key
        except Exception:
            pass

        url = f"{base_url}/message/sendText/{instance_name}"
        headers = {"apikey": api_key, "Content-Type": "application/json"}
        payload = {
            "number": phone,
            "text": text
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=20)
            if resp.status_code < 400:
                logger.info(f"Real WhatsApp notification sent to {phone} via Evolution API ({instance_name})")
                return True
            else:
                logger.error(f"Failed to send WA message via Evolution API ({instance_name}): {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending WA message via Evolution API ({instance_name}): {e}")
            return False

    def _send_whatsapp_notification_chunked(self, phone, text, chunk_size=3500):
        lines = str(text or "").splitlines()
        if not lines:
            return self._send_whatsapp_notification(phone, str(text or ""))
        chunks = []
        current = []
        current_len = 0
        for line in lines:
            line_len = len(line) + 1
            if current and current_len + line_len > int(chunk_size):
                chunks.append("\n".join(current).strip())
                current = [line]
                current_len = line_len
            else:
                current.append(line)
                current_len += line_len
        if current:
            chunks.append("\n".join(current).strip())
        overall = True
        for idx, chunk in enumerate(chunks, start=1):
            prefix = f"[Part {idx}/{len(chunks)}]\n" if len(chunks) > 1 else ""
            ok = self._send_whatsapp_notification(phone, prefix + chunk)
            overall = overall and ok
            time.sleep(0.4)
        return overall

    def _lookup_latest_conversation_by_record_id(self, record_id):
        record_id = str(record_id or "").strip()
        if not record_id:
            return None
        try:
            import sqlite3
            with sqlite3.connect("chat_history.db", timeout=15.0) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT chat_id, sender_identifier, customer_phone, contact_name, source, last_customer_channel, location, receiving_phone_id
                    FROM conversations
                    WHERE airtable_record_id = ?
                    ORDER BY rowid DESC
                    LIMIT 1
                    """,
                    (record_id,),
                )
                row = cur.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to lookup conversation by record_id {record_id}: {e}")
            return None

    def _collect_ticket_attachments(self, fields):
        fields = fields if isinstance(fields, dict) else {}

        def _normalize_entries(raw_value, source_field):
            entries = []
            if isinstance(raw_value, str):
                raw_items = [{"url": raw_value, "filename": source_field or "document"}]
            elif isinstance(raw_value, dict):
                raw_items = [raw_value]
            elif isinstance(raw_value, list):
                raw_items = raw_value
            else:
                raw_items = []
            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                url = str(item.get("url") or "").strip()
                if not url:
                    continue
                filename = str(item.get("filename") or item.get("name") or source_field or "document").strip() or "document"
                mime_type = str(item.get("type") or "").strip().lower()
                url_no_qs = url.split("?", 1)[0].lower()
                is_image = (
                    filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")) or
                    url_no_qs.endswith((".png", ".jpg", ".jpeg", ".webp")) or
                    mime_type.startswith("image/")
                )
                is_pdf = (
                    filename.lower().endswith(".pdf") or
                    url_no_qs.endswith(".pdf") or
                    mime_type.startswith("application/pdf")
                )
                entries.append({
                    "url": url,
                    "filename": filename,
                    "type": mime_type or "application/octet-stream",
                    "source_field": source_field,
                    "is_image": bool(is_image),
                    "is_pdf": bool(is_pdf),
                })
            return entries

        entries = []
        entries.extend(_normalize_entries(fields.get("Tickets Files"), "Tickets Files"))
        entries.extend(_normalize_entries(fields.get("Attachments"), "Attachments"))
        entries = [item for item in entries if not item.get("is_image")]
        pdf_entries = [item for item in entries if item.get("is_pdf")]
        return pdf_entries or entries

    def _download_attachment_bytes(self, url):
        try:
            response = requests.get(str(url or "").strip(), timeout=60)
            if response.status_code >= 400:
                logger.error("Failed to download attachment %s: %s", str(url or ""), response.text[:400])
                return None
            return response.content
        except Exception as e:
            logger.error("Request error while downloading attachment %s: %s", str(url or ""), e)
            return None

    def _send_ticket_attachments_to_chat(self, chat_id, attachments, location="Unknown", receiving_phone_id=None):
        chat_id = str(chat_id or "").strip()
        if not chat_id:
            return {"ok": False, "sent_count": 0, "errors": ["missing_chat_id"]}
        sent_count = 0
        errors = []
        actor = json.dumps({
            "id": "pi_background_engine",
            "name": "PI Background Engine",
            "role": "system",
        }, ensure_ascii=False)
        for idx, attachment in enumerate(attachments or [], start=1):
            file_url = str((attachment or {}).get("url") or "").strip()
            filename = str((attachment or {}).get("filename") or f"ticket_{idx}.pdf").strip() or f"ticket_{idx}.pdf"
            file_bytes = self._download_attachment_bytes(file_url)
            if not file_bytes:
                errors.append(f"download_failed:{filename}")
                continue
            files = {
                "file": (
                    filename,
                    file_bytes,
                    str((attachment or {}).get("type") or "application/octet-stream") or "application/octet-stream",
                )
            }
            data = {
                "chat_id": chat_id,
                "text": f"Ticket PDF - {filename}",
                "reply_channel": "whatsapp",
                "location": str(location or "Unknown").strip() or "Unknown",
                "actor": actor,
            }
            if str(receiving_phone_id or "").strip():
                data["receiving_phone_id"] = str(receiving_phone_id).strip()
            try:
                send_resp = requests.post(
                    "http://127.0.0.1:5001/api/chats/send",
                    data=data,
                    files=files,
                    timeout=120,
                )
                try:
                    send_json = send_resp.json()
                except Exception:
                    send_json = {"raw": send_resp.text}
                if send_resp.status_code >= 400 or str(send_json.get("status") or "").strip().lower() != "success":
                    errors.append(f"send_failed:{filename}:{_payload_preview(send_json)}")
                    continue
                sent_count += 1
            except Exception as e:
                errors.append(f"send_exception:{filename}:{e}")
        return {"ok": bool(sent_count > 0 and not errors), "sent_count": sent_count, "errors": errors}

    def process_outbox(self, user_dir):
        """
        قراءة الـ Manifests الموجودة في الـ Outbox وتنفيذها.
        إذا كان الإجراء هو add_watcher، يتم حفظه في مجلد الـ watchers الخاص بالمستخدم.
        """
        outbox_dir = os.path.join(user_dir, "bridge", "outbox")
        inbox_dir = os.path.join(user_dir, "bridge", "inbox")
        watchers_dir = os.path.join(user_dir, "management", "watchers")
        
        os.makedirs(outbox_dir, exist_ok=True)
        os.makedirs(inbox_dir, exist_ok=True)
        os.makedirs(watchers_dir, exist_ok=True)
        
        manifest_files = glob.glob(os.path.join(outbox_dir, "*.json"))
        for file_path in manifest_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                
                # لا نتخطى الـ manifests الخاصة بالمراقب حتى يتم إرسال الإشعار
                # if manifest.get("intent") == "watcher_triggered_execution":
                #     continue
                
                logger.info(f"Processing Manifest: {manifest.get('manifest_id')} for user {os.path.basename(user_dir)}")
                logger.info(
                    "Manifest details | intent=%s | action_count=%s | payload=%s",
                    str(manifest.get("intent") or "").strip(),
                    len(manifest.get("actions") or []),
                    _payload_preview(manifest),
                )
                
                result = {
                    "manifest_id": manifest.get("manifest_id"),
                    "status": "success",
                    "executed_at": datetime.now().isoformat(),
                    "actions_results": []
                }
                
                for action in manifest.get("actions", []):
                    action_type = str(action.get("type") or "").strip().lower()
                    logger.info(
                        "Manifest action start | manifest_id=%s | action_type=%s | payload=%s",
                        str(manifest.get("manifest_id") or "").strip(),
                        str(action_type or "").strip(),
                        _payload_preview(action.get("payload", {})),
                    )
                    #region debug-point capability-dev-str-get.action_shape
                    _dbg_emit(
                        "process_outbox.action_shape",
                        {
                            "manifest_id": str(manifest.get("manifest_id") or "").strip(),
                            "action_type": str(action_type or "").strip(),
                            "action_py_type": str(type(action)),
                            "has_payload_key": isinstance(action, dict) and ("payload" in action),
                            "payload_py_type": str(type(action.get("payload"))) if isinstance(action, dict) else "n/a",
                        },
                    )
                    #endregion debug-point capability-dev-str-get.action_shape
                    
                    if action_type == "add_watcher":
                        # تسجيل الـ Watcher الجديد
                        watcher_id = f"watcher_{uuid.uuid4().hex[:8]}"
                        watcher_path = os.path.join(watchers_dir, f"{watcher_id}.json")
                        with open(watcher_path, "w", encoding="utf-8") as wf:
                            json.dump(action, wf, ensure_ascii=False, indent=2)
                        
                        result["actions_results"].append({
                            "action_type": action_type,
                            "status": "executed",
                            "message": f"Watcher {watcher_id} registered successfully."
                        })
                    elif action_type == "schedule_task":
                        # تسجيل مهمة مجدولة جديدة
                        tasks_dir = os.path.join(user_dir, "management", "scheduled_tasks")
                        os.makedirs(tasks_dir, exist_ok=True)
                        task_id = f"task_{uuid.uuid4().hex[:8]}"
                        
                        # معالجة الأوقات النسبية (مثل '+1 hour') وتحويلها إلى وقت مطلق
                        execute_at_str = action.get("execute_at", "")
                        execute_time = None
                        
                        try:
                            if execute_at_str.startswith("+"):
                                parts = execute_at_str.strip().split()
                                if len(parts) >= 2:
                                    amount = int(parts[0][1:])
                                    unit = parts[1].lower()
                                    if "sec" in unit:
                                        execute_time = datetime.now().timestamp() + amount
                                    elif "min" in unit:
                                        execute_time = datetime.now().timestamp() + (amount * 60)
                                    elif "hour" in unit:
                                        execute_time = datetime.now().timestamp() + (amount * 3600)
                                    elif "day" in unit:
                                        execute_time = datetime.now().timestamp() + (amount * 86400)
                            else:
                                # افتراض أنه ISO format
                                dt = datetime.fromisoformat(execute_at_str.replace("Z", "+00:00"))
                                execute_time = dt.timestamp()
                        except Exception as e:
                            logger.error(f"Failed to parse execute_at '{execute_at_str}': {e}")
                            
                        if not execute_time:
                            # إذا فشل التحليل، نضع وقت افتراضي بعد 5 دقائق من الآن
                            execute_time = datetime.now().timestamp() + 300
                            
                        action["execute_timestamp"] = execute_time
                        
                        task_path = os.path.join(tasks_dir, f"{task_id}.json")
                        with open(task_path, "w", encoding="utf-8") as tf:
                            json.dump(action, tf, ensure_ascii=False, indent=2)
                            
                        result["actions_results"].append({
                            "action_type": action_type,
                            "status": "executed",
                            "message": f"Task {task_id} scheduled for {datetime.fromtimestamp(execute_time).isoformat()}."
                        })
                    elif action_type in ["send_internal_notification", "send_reminder_message", "send_internal_notification_invoice_pending"] or "send" in str(action_type).lower() or "notif" in str(action_type).lower():
                        # إرسال رسالة واتساب فعلية للمستخدم
                        payload = action.get("payload", {})
                        message = payload.get("message")

                        if not message:
                            if "invoice" in str(action_type).lower():
                                message = f"🔔 إشعار من PI: لقد تغيرت الحالة للحجز {action.get('target_record')} كما طلبت."
                            else:
                                message = f"🔔 إشعار من PI: تحقق شرط المراقبة للحجز {action.get('target_record')}\nالرجاء المراجعة."
                                
                        # تحديد المستلم: الهاتف المرسل مع الـ action أو الافتراضي Ahmady
                        admin_phone = str(
                            action.get("phone")
                            or payload.get("phone")
                            or "201010323484"
                        ).strip()
                        
                        success = self._send_whatsapp_notification(admin_phone, message)
                        
                        result["actions_results"].append({
                            "action_type": action_type,
                            "status": "executed" if success else "failed",
                            "message": "Real WhatsApp notification sent." if success else "Failed to send WhatsApp notification."
                        })
                    elif action_type == "query_records":
                        payload = action.get("payload", {})
                        target_table = payload.get("target_table", "Bookings_List")
                        date_type = payload.get("date_type", "")
                        date_value = payload.get("date_value", "")
                        agency_filter = payload.get("agency_filter", "")
                        status_filter = payload.get("status_filter", "")

                        api_key = self.airtable_config.get("api_key")
                        base_id = self.airtable_config.get("base_id")
                        
                        if target_table == "Catalog_MPC":
                            table_name = "MPC"
                        elif target_table == "Website_Trips":
                            base_id = self.airtable_config.get("trips_base_id") or base_id
                            table_name = "Trips"
                        else:
                            table_name = self.airtable_config.get("tables", {}).get("main_list", "List")

                        if not api_key or not base_id:
                            result["actions_results"].append({
                                "action_type": action_type,
                                "status": "failed",
                                "message": "Missing Airtable API Key or Base ID."
                            })
                        else:
                            try:
                                url = f"https://api.airtable.com/v0/{base_id}/{quote(table_name)}"
                                headers = {"Authorization": f"Bearer {api_key}"}
                                
                                formulas = []
                                if agency_filter:
                                    formulas.append(f"FIND('{agency_filter}', {{Real Product Name}})")
                                if status_filter:
                                    formulas.append(f"FIND('{status_filter}', {{Booking Status}})")
                                if date_value and date_type:
                                    if str(date_value or "").strip().lower() == "today":
                                        target_date_str = self._current_cairo_date_str(day_offset=0)
                                    elif str(date_value or "").strip().lower() == "tomorrow":
                                        target_date_str = self._current_cairo_date_str(day_offset=1)
                                    else:
                                        target_date_str = str(date_value or "").strip()
                                    resolved_date_field = self._resolve_query_date_field_name(date_type)
                                    # Keep Create Date filtering on Python side so Cairo timezone conversion remains correct.
                                    if resolved_date_field and target_date_str and resolved_date_field != "Create Date  ":
                                        formulas.append(f"IS_SAME({{{resolved_date_field}}}, '{target_date_str}', 'day')")
                                    
                                filter_formula = ""
                                if len(formulas) > 1:
                                    filter_formula = f"AND({','.join(formulas)})"
                                elif len(formulas) == 1:
                                    filter_formula = formulas[0]

                                params = {}
                                if filter_formula:
                                    params["filterByFormula"] = filter_formula

                                response = requests.get(url, headers=headers, params=params, timeout=30)
                                if response.status_code == 200:
                                    records = self._fetch_airtable_records_paginated(url, headers, params=params)
                                    
                                    # Python-side filtering for dates
                                    filtered_records = []
                                    for r in records:
                                        fields = r.get("fields", {})
                                        keep = True
                                        
                                        # Simple date filter logic for "today"
                                        if date_value and date_type:
                                            target_date_str = ""
                                            if date_value.lower() == "today":
                                                target_date_str = self._current_cairo_date_str(day_offset=0)
                                            elif date_value.lower() == "tomorrow":
                                                target_date_str = self._current_cairo_date_str(day_offset=1)
                                            else:
                                                target_date_str = str(date_value or "").strip() # assume YYYY-MM-DD
                                            record_date = self._resolve_record_date_value(fields, date_type)
                                            if self._extract_date_only(record_date) != self._extract_date_only(target_date_str):
                                                keep = False
                                                
                                        if keep:
                                            filtered_records.append(fields)

                                    # Format message to send back to user
                                    msg_lines = [f"🔔 *نتيجة استعلام PI ({target_table})*:\n"]
                                    target_date_display = ""
                                    if str(date_value or "").strip().lower() == "today":
                                        target_date_display = f"today ({self._current_cairo_date_str(day_offset=0)})"
                                    elif str(date_value or "").strip().lower() == "tomorrow":
                                        target_date_display = f"tomorrow ({self._current_cairo_date_str(day_offset=1)})"
                                    else:
                                        target_date_display = str(date_value or "").strip()
                                    scope_parts = [f"Table: {table_name}"]
                                    if date_type:
                                        scope_parts.append(f"Date Field: {date_type}")
                                    if target_date_display:
                                        scope_parts.append(f"Date Filter: {target_date_display}")
                                    if agency_filter:
                                        scope_parts.append(f"Agency Filter: {agency_filter}")
                                    if status_filter:
                                        scope_parts.append(f"Status Filter: {status_filter}")
                                    if scope_parts:
                                        msg_lines.append("الفلاتر المستخدمة:")
                                        for part in scope_parts:
                                            msg_lines.append(f"- {part}")
                                        msg_lines.append("")
                                    display_records = filtered_records
                                    if target_table == "Catalog_MPC":
                                        deduped_records = []
                                        seen_trip_keys = set()
                                        for fields in filtered_records:
                                            trip_label = str(fields.get("Trip name correction") or "").strip()
                                            trip_key = trip_label.strip().lower()
                                            if not trip_label or trip_key in seen_trip_keys:
                                                continue
                                            seen_trip_keys.add(trip_key)
                                            deduped_records.append(fields)
                                        display_records = deduped_records
                                    msg_lines.append(f"تم العثور على {len(display_records)} نتيجة مطابقة:\n")
                                    
                                    for idx, fields in enumerate(display_records, 1):
                                        if target_table == "Catalog_MPC":
                                            t_name = fields.get("Trip name correction") or fields.get("Main Product Name") or fields.get("Name") or "Unknown"
                                            ref_value = fields.get("ID") or fields.get("Product ID") or "N/A"
                                            ref_label = "ID"
                                        else:
                                            t_name = fields.get("trip Name") or fields.get("trip name") or fields.get("Trip Name") or fields.get("Real Product Name") or "Unknown"
                                            ref_value = fields.get("Booking Nr.") or "N/A"
                                            ref_label = "Booking"
                                        customer_name = fields.get("Customer Name") or "Unknown"
                                        record_date = self._resolve_record_date_value(fields, date_type) if date_type else ""
                                        status = fields.get("Booking Status") or fields.get("Status") or "N/A"
                                        msg_lines.append(
                                            f"{idx}. {t_name}\n"
                                            f"   ({ref_label}: {ref_value} | Customer: {customer_name} | "
                                            f"{date_type or 'Date'}: {self._extract_date_only(record_date) or 'N/A'} | Status: {status})"
                                        )

                                    final_msg = "\n".join(msg_lines)
                                    admin_phone = "201010323484"
                                    success = self._send_whatsapp_notification_chunked(admin_phone, final_msg)
                                    
                                    result["actions_results"].append({
                                        "action_type": action_type,
                                        "status": "executed" if success else "failed",
                                        "message": f"Successfully fetched and sent {len(display_records)} records."
                                    })
                                else:
                                    result["actions_results"].append({
                                        "action_type": action_type,
                                        "status": "failed",
                                        "message": f"Airtable API Error: {response.text}"
                                    })
                            except Exception as e:
                                result["actions_results"].append({
                                    "action_type": action_type,
                                    "status": "failed",
                                    "message": str(e)
                                })
                    
                    elif action_type == "develop_new_capability":
                        try:
                            payload = action.get("payload", {})
                            payload_input_type = type(payload)
                            #region debug-point capability-dev-str-get.develop_new_capability_payload
                            preview = None
                            preview_keys = None
                            if isinstance(payload, dict):
                                preview_keys = list(payload.keys())[:30]
                            else:
                                preview = str(payload)[:200]
                            _dbg_emit(
                                "develop_new_capability.payload_shape",
                                {
                                    "manifest_id": str(manifest.get("manifest_id") or "").strip(),
                                    "action_py_type": str(type(action)),
                                    "payload_py_type": str(type(payload)),
                                    "payload_keys": preview_keys,
                                    "payload_preview": preview,
                                },
                            )
                            #endregion debug-point capability-dev-str-get.develop_new_capability_payload
                            if isinstance(payload, str):
                                raw_payload = payload.strip()
                                try:
                                    if raw_payload.startswith("{") and raw_payload.endswith("}"):
                                        payload = json.loads(raw_payload)
                                except Exception:
                                    payload = None
                            if not isinstance(payload, dict):
                                if payload_input_type is str:
                                    raise ValueError("Invalid develop_new_capability payload: expected an object, got string.")
                                raise ValueError(f"Invalid develop_new_capability payload: expected an object, got {payload_input_type}.")
                            tool_name = payload.get("tool_name", "unknown_tool")
                            tool_desc = payload.get("tool_description", "")
                            param_schema = payload.get("parameters_schema", {})
                            python_code = payload.get("python_code", "")
                
                            if not tool_name or not python_code:
                                raise ValueError("tool_name and python_code are required")
                
                            # 1. Save Schema
                            schema_dir = os.path.join("runtime", "pi_brain", "schemas")
                            os.makedirs(schema_dir, exist_ok=True)
                            schema_path = os.path.join(schema_dir, f"{tool_name}_schema.json")
                
                            schema_obj = {
                                "name": tool_name,
                                "description": tool_desc,
                                "parameters": {
                                    "type": "object",
                                    "properties": param_schema.get("properties", param_schema) if "properties" in param_schema else param_schema,
                                    "required": param_schema.get("required", [])
                                }
                            }
                
                            with open(schema_path, 'w', encoding='utf-8') as sf:
                                json.dump(schema_obj, sf, ensure_ascii=False, indent=2)
                
                            # 2. Save Python Handler
                            handlers_dir = os.path.join("runtime", "pi_brain", "dynamic_handlers")
                            os.makedirs(handlers_dir, exist_ok=True)
                            handler_path = os.path.join(handlers_dir, f"{tool_name}.py")
                
                            with open(handler_path, 'w', encoding='utf-8') as hf:
                                hf.write(python_code)
                
                            result["status"] = "success"
                            result["message"] = f"تم إنشاء الأداة الجديدة '{tool_name}' بنجاح وهي الآن جاهزة للاستخدام في النظام."
                        except Exception as e:
                            result["status"] = "error"
                            result["message"] = f"Failed to develop new capability: {e}"
                            logging.error(f"Capability Dev Error: {e}")

                    elif action_type in ["update_record", "update_airtable"]:
                                    # تحديث مباشر في Airtable
                        payload = action.get("payload", {})
                        target_record = action.get("target_record") or action.get("record_id") or (payload.get("record_id") if isinstance(payload, dict) else None)
                        actual_updates = {}
                        base_type = str(action.get("base_type") or "").strip() or "main"
                        table_name = ""
                        field_types = {}
                        is_religious = None
                        if isinstance(payload, dict):
                            if isinstance(payload.get("fields"), dict):
                                actual_updates = payload.get("fields") or {}
                            else:
                                actual_updates = dict(payload)
                                actual_updates.pop("record_id", None)
                                actual_updates.pop("table_name", None)
                                actual_updates.pop("base_type", None)
                                actual_updates.pop("field_types", None)
                                actual_updates.pop("is_religious", None)
                            table_name = str(payload.get("table_name") or action.get("table_name") or "").strip()
                            field_types = payload.get("field_types") if isinstance(payload.get("field_types"), dict) else {}
                            if payload.get("base_type"):
                                base_type = str(payload.get("base_type") or "").strip()
                            if "is_religious" in payload:
                                is_religious = bool(payload.get("is_religious"))
                        else:
                            actual_updates = {}
                        if not target_record or not actual_updates:
                            result["actions_results"].append({
                                "action_type": action_type,
                                "status": "failed",
                                "message": "Missing target_record or payload for update."
                            })
                        else:
                            success = self._update_airtable_record(
                                target_record,
                                actual_updates,
                                base_type=base_type,
                                table_name=table_name,
                                field_types=field_types,
                                is_religious=is_religious,
                            )
                            result["actions_results"].append({
                                "action_type": action_type,
                                "status": "executed" if success else "failed",
                                "message": f"Updated Airtable record {target_record}." if success else "Failed to update Airtable record."
                            })
                            admin_phone = "201010323484"
                            fields_str = ", ".join([f"{k}: {v}" for k, v in actual_updates.items()])
                            if success:
                                self._send_whatsapp_notification(
                                    admin_phone,
                                    f"✅ تم تحديث السجل {target_record} بنجاح.\nالتحديثات: {fields_str}",
                                )
                            else:
                                self._send_whatsapp_notification(
                                    admin_phone,
                                    f"❌ فشل تحديث السجل {target_record}.\nالتحديثات: {fields_str}\n[ESCALATE]",
                                )
                    elif action_type == "create_invoice":
                        payload = action.get("payload", {}) if isinstance(action.get("payload"), dict) else {}
                        target_record = str(
                            action.get("target_record")
                            or action.get("record_id")
                            or payload.get("record_id")
                            or ""
                        ).strip()
                        amount = payload.get("amount")
                        currency = str(payload.get("currency") or "").strip() or None
                        selected_add_ons = payload.get("selected_add_ons")
                        send_after_create = bool(payload.get("send_after_create", True))
                        preferred_template_name = str(
                            payload.get("template_name")
                            or payload.get("whatsapp_template_name")
                            or action.get("preferred_template_name")
                            or action.get("template_name")
                            or ""
                        ).strip()
                        preferred_template_language = str(
                            payload.get("template_language")
                            or payload.get("whatsapp_template_language")
                            or action.get("preferred_template_language")
                            or action.get("template_language")
                            or "en"
                        ).strip() or "en"
                        booking_number = str(
                            action.get("booking_number")
                            or payload.get("booking_number")
                            or target_record
                        ).strip() or target_record
                        resolved_target_record = self._resolve_main_booking_record_id(target_record or booking_number)
                        admin_phone = str(payload.get("admin_phone") or "201010323484").strip() or "201010323484"
                        if not resolved_target_record:
                            result["actions_results"].append({
                                "action_type": action_type,
                                "status": "error",
                                "message": f"Missing or unresolved target_record for create_invoice: {target_record or booking_number}"
                            })
                            self._send_whatsapp_notification(
                                admin_phone,
                                f"❌ فشل إنشاء الفاتورة: لا يوجد target_record صالح أو لم يتم العثور على الحجز `{booking_number}`.\n[ESCALATE]",
                            )
                        else:
                            try:
                                create_payload = {
                                    "record_id": resolved_target_record,
                                    "amount": amount,
                                    "currency": currency,
                                    "selected_add_ons": selected_add_ons,
                                }
                                create_resp = requests.post(
                                    "http://127.0.0.1:5001/api/payments/create",
                                    json=create_payload,
                                    timeout=60,
                                )
                                try:
                                    create_json = create_resp.json()
                                except Exception:
                                    create_json = {"raw": create_resp.text}
                                if create_resp.status_code >= 400 or str(create_json.get("status") or "").strip().lower() != "success":
                                    raise ValueError(f"Payment creation failed: {create_json}")
                                payment_url = str(create_json.get("payment_url") or "").strip()
                                booking_record = self._fetch_airtable_record(resolved_target_record)
                                booking_fields = (booking_record or {}).get("fields") if isinstance((booking_record or {}).get("fields"), dict) else {}
                                send_note = ""
                                if send_after_create:
                                    conv = self._lookup_latest_conversation_by_record_id(resolved_target_record)
                                    chat_id = str((conv or {}).get("chat_id") or "").strip()
                                    if not chat_id:
                                        raise ValueError("Invoice created but no conversation/chat_id found to send it to the customer.")
                                    customer_name = str((conv or {}).get("contact_name") or "Guest").strip() or "Guest"
                                    send_location = str((conv or {}).get("location") or payload.get("location") or "Unknown").strip() or "Unknown"
                                    send_receiving_phone_id = str((conv or {}).get("receiving_phone_id") or payload.get("receiving_phone_id") or "").strip()
                                    chosen_template_name = self._resolve_invoice_template_name(preferred_template_name, send_location)
                                    template_variables = self._build_invoice_template_variables(booking_fields, payment_url)
                                    message_text = (
                                        f"Hello {customer_name},\n"
                                        f"Here is your payment link for booking {booking_number}:\n"
                                        f"{payment_url}\n"
                                        "Please let us know once the payment is completed."
                                    )
                                    base_send_payload = {
                                        "chat_id": chat_id,
                                        "reply_channel": "whatsapp",
                                        "location": send_location,
                                        "receiving_phone_id": send_receiving_phone_id,
                                        "actor": {
                                            "id": "pi_background_engine",
                                            "name": "PI Background Engine",
                                            "role": "system",
                                        },
                                    }
                                    if preferred_template_name:
                                        send_resp = requests.post(
                                            "http://127.0.0.1:5001/api/chats/send",
                                            json={
                                                **base_send_payload,
                                                "text": "",
                                                "template_name": chosen_template_name,
                                                "template_language": preferred_template_language,
                                                "booking_data": booking_fields,
                                                "template_variables": template_variables,
                                            },
                                            timeout=60,
                                        )
                                        try:
                                            send_json = send_resp.json()
                                        except Exception:
                                            send_json = {"raw": send_resp.text}
                                        if send_resp.status_code >= 400 or str(send_json.get("status") or "").strip().lower() != "success":
                                            raise ValueError(f"Invoice created but template send failed: {send_json}")
                                        send_note = f" and sent to customer via template `{chosen_template_name}`"
                                    else:
                                        send_resp = requests.post(
                                            "http://127.0.0.1:5001/api/chats/send",
                                            json={
                                                **base_send_payload,
                                                "text": message_text,
                                            },
                                            timeout=60,
                                        )
                                        try:
                                            send_json = send_resp.json()
                                        except Exception:
                                            send_json = {"raw": send_resp.text}
                                        send_ok = send_resp.status_code < 400 and str(send_json.get("status") or "").strip().lower() == "success"
                                        send_code = str(send_json.get("code") or "").strip()
                                        if not send_ok and send_code == "WHATSAPP_WINDOW_CLOSED":
                                            fallback_resp = requests.post(
                                                "http://127.0.0.1:5001/api/chats/send",
                                                json={
                                                    **base_send_payload,
                                                    "text": "",
                                                    "template_name": chosen_template_name,
                                                    "template_language": preferred_template_language,
                                                    "booking_data": booking_fields,
                                                    "template_variables": template_variables,
                                                },
                                                timeout=60,
                                            )
                                            try:
                                                fallback_json = fallback_resp.json()
                                            except Exception:
                                                fallback_json = {"raw": fallback_resp.text}
                                            if fallback_resp.status_code >= 400 or str(fallback_json.get("status") or "").strip().lower() != "success":
                                                raise ValueError(
                                                    f"Invoice created, text send hit WHATSAPP_WINDOW_CLOSED, and template fallback failed: {fallback_json}"
                                                )
                                            send_note = f" and sent to customer via template fallback `{chosen_template_name}`"
                                        elif not send_ok:
                                            raise ValueError(f"Invoice created but customer send failed: {send_json}")
                                        else:
                                            send_note = " and sent to customer"
                                result["actions_results"].append({
                                    "action_type": action_type,
                                    "status": "executed",
                                    "message": f"Invoice created{send_note} for {booking_number}. Payment URL: {payment_url}"
                                })
                                self._send_whatsapp_notification(
                                    admin_phone,
                                    f"✅ تم إنشاء الفاتورة للحجز {booking_number}{send_note}.\nالرابط: {payment_url}",
                                )
                            except Exception as e:
                                logger.error(
                                    "Manifest create_invoice failed | manifest_id=%s | target_record=%s | resolved_target_record=%s | error=%s",
                                    str(manifest.get("manifest_id") or "").strip(),
                                    target_record,
                                    resolved_target_record,
                                    str(e),
                                )
                                result["actions_results"].append({
                                    "action_type": action_type,
                                    "status": "error",
                                    "message": f"Invoice execution failed: {e}"
                                })
                                self._send_whatsapp_notification(
                                    admin_phone,
                                    f"❌ فشل إنشاء/إرسال الفاتورة للحجز {booking_number}.\nالسبب: {e}\n[ESCALATE]",
                                )
                    elif action_type == "fetch_booking" and isinstance(action.get("payload"), dict):
                        payload = action.get("payload", {}) if isinstance(action.get("payload"), dict) else {}
                        requested_action = str(payload.get("action") or "").strip().lower()
                        booking_number = str(
                            payload.get("booking_number")
                            or action.get("booking_number")
                            or action.get("target_record")
                            or ""
                        ).strip()
                        target_hint = str(action.get("target_record") or payload.get("record_id") or booking_number).strip()
                        resolved_target_record = self._resolve_main_booking_record_id(target_hint)
                        admin_phone = str(payload.get("admin_phone") or "201010323484").strip() or "201010323484"
                        if requested_action == "send_ticket":
                            if not resolved_target_record:
                                result["actions_results"].append({
                                    "action_type": action_type,
                                    "status": "error",
                                    "message": f"Could not resolve booking `{booking_number or target_hint}` to an Airtable record."
                                })
                                self._send_whatsapp_notification(
                                    admin_phone,
                                    f"❌ فشل إرسال التذكرة: لم أستطع العثور على الحجز `{booking_number or target_hint}`.\n[ESCALATE]",
                                )
                            else:
                                booking_record = self._fetch_airtable_record(resolved_target_record)
                                booking_fields = (booking_record or {}).get("fields") if isinstance((booking_record or {}).get("fields"), dict) else {}
                                attachments = self._collect_ticket_attachments(booking_fields)
                                conv = self._lookup_latest_conversation_by_record_id(resolved_target_record)
                                chat_id = str((conv or {}).get("chat_id") or "").strip()
                                send_location = str((conv or {}).get("location") or payload.get("location") or "Unknown").strip() or "Unknown"
                                send_receiving_phone_id = str((conv or {}).get("receiving_phone_id") or payload.get("receiving_phone_id") or "").strip()
                                if not attachments:
                                    msg = f"No ticket/document attachments found in Airtable for booking {booking_number or resolved_target_record}."
                                    result["actions_results"].append({
                                        "action_type": action_type,
                                        "status": "error",
                                        "message": msg,
                                    })
                                    self._send_whatsapp_notification(
                                        admin_phone,
                                        f"❌ {msg}\n[ESCALATE]",
                                    )
                                elif not chat_id:
                                    msg = f"No customer conversation/chat_id found to send ticket attachments for booking {booking_number or resolved_target_record}."
                                    result["actions_results"].append({
                                        "action_type": action_type,
                                        "status": "error",
                                        "message": msg,
                                    })
                                    self._send_whatsapp_notification(
                                        admin_phone,
                                        f"❌ {msg}\n[ESCALATE]",
                                    )
                                else:
                                    attachment_links = [
                                        str((item or {}).get("url") or "").strip()
                                        for item in (attachments or [])
                                        if str((item or {}).get("url") or "").strip()
                                    ]
                                    links_preview = "\n".join(f"- {link}" for link in attachment_links[:5])
                                    send_result = self._send_ticket_attachments_to_chat(
                                        chat_id,
                                        attachments,
                                        location=send_location,
                                        receiving_phone_id=send_receiving_phone_id,
                                    )
                                    if send_result.get("sent_count"):
                                        msg = (
                                            f"Sent {int(send_result.get('sent_count') or 0)} ticket/document file(s) "
                                            f"for booking {booking_number or resolved_target_record}."
                                        )
                                        if links_preview:
                                            msg = f"{msg} Links:\n{links_preview}"
                                        if send_result.get("errors"):
                                            msg = f"{msg} Partial issues: {' | '.join(send_result.get('errors') or [])}"
                                        result["actions_results"].append({
                                            "action_type": action_type,
                                            "status": "executed" if not send_result.get("errors") else "error",
                                            "message": msg,
                                        })
                                        result["result_preview"] = msg
                                        result["internal_reply"] = msg
                                        admin_notice = (
                                            f"✅ تم إرسال {int(send_result.get('sent_count') or 0)} ملف/تذكرة للحجز {booking_number or resolved_target_record}."
                                        )
                                        if links_preview:
                                            admin_notice = f"{admin_notice}\nالروابط:\n{links_preview}"
                                        self._send_whatsapp_notification(
                                            admin_phone,
                                            admin_notice,
                                        )
                                    else:
                                        msg = (
                                            f"Ticket send failed for booking {booking_number or resolved_target_record}: "
                                            f"{' | '.join(send_result.get('errors') or ['unknown_error'])}"
                                        )
                                        result["actions_results"].append({
                                            "action_type": action_type,
                                            "status": "error",
                                            "message": msg,
                                        })
                                        self._send_whatsapp_notification(
                                            admin_phone,
                                            f"❌ فشل إرسال التذكرة للحجز {booking_number or resolved_target_record}.\nالسبب: {' | '.join(send_result.get('errors') or ['unknown_error'])}\n[ESCALATE]",
                                        )
                        else:
                            result["actions_results"].append({
                                "action_type": action_type,
                                "status": "executed",
                                "message": f"fetch_booking recognized, but no executor is defined for action `{requested_action or 'unknown'}`."
                            })
                    else:
                        # Check if there's a dynamic handler
                        handlers_dir = os.path.join("runtime", "pi_brain", "dynamic_handlers")
                        handler_path = os.path.join(handlers_dir, f"{action_type}.py")
                        payload = action.get("payload", {})
                        if os.path.exists(handler_path):
                            try:
                                import importlib.util
                                import sys
                                
                                spec = importlib.util.spec_from_file_location(f"dynamic_{action_type}", handler_path)
                                mod = importlib.util.module_from_spec(spec)
                                sys.modules[f"dynamic_{action_type}"] = mod
                                spec.loader.exec_module(mod)
                                
                                if hasattr(mod, f"handle_{action_type}"):
                                    handler_func = getattr(mod, f"handle_{action_type}")
                                    actor_name = os.path.basename(user_dir)
                                    dynamic_result = handler_func(payload, actor_name)
                                    logger.info(
                                        "Manifest action result | manifest_id=%s | action_type=%s | dynamic_result=%s",
                                        str(manifest.get("manifest_id") or "").strip(),
                                        str(action_type or "").strip(),
                                        _payload_preview(dynamic_result),
                                    )
                                    result["actions_results"].append({
                                        "action_type": action_type,
                                        "status": dynamic_result.get("status", "executed"),
                                        "message": dynamic_result.get("message", "Dynamic action executed.")
                                    })
                                    notify_admin = bool(isinstance(payload, dict) and payload.get("notify_admin"))
                                    if notify_admin and isinstance(dynamic_result, dict):
                                        admin_phone = str(payload.get("admin_phone") or "201010323484").strip() or "201010323484"
                                        status_txt = str(dynamic_result.get("status") or "").strip().lower()
                                        prefix = "✅" if status_txt == "success" else "❌"
                                        msg = str(dynamic_result.get("message") or "").strip()
                                        if not msg:
                                            msg = "Dynamic action executed."
                                        if prefix == "❌" and "[ESCALATE]" not in msg:
                                            msg = f"{msg}\n[ESCALATE]"
                                        self._send_whatsapp_notification(
                                            admin_phone,
                                            f"{prefix} {msg}",
                                        )
                                else:
                                    result["actions_results"].append({
                                        "action_type": action_type,
                                        "status": "error",
                                        "message": f"Dynamic handler missing 'handle_{action_type}'."
                                    })
                            except Exception as e:
                                logger.error(
                                    "Manifest action exception | manifest_id=%s | action_type=%s | error=%s",
                                    str(manifest.get("manifest_id") or "").strip(),
                                    str(action_type or "").strip(),
                                    str(e),
                                )
                                result["actions_results"].append({
                                    "action_type": action_type,
                                    "status": "error",
                                    "message": f"Dynamic execution failed: {e}"
                                })
                        else:
                            # محاكاة التنفيذ للإجراءات الأخرى
                            result["actions_results"].append({
                                "action_type": action_type,
                                "status": "executed",
                                "message": f"Action {action_type} processed safely via Guard (No dynamic handler found)."
                            })

                action_statuses = [
                    str((item or {}).get("status") or "").strip().lower()
                    for item in (result.get("actions_results") or [])
                    if isinstance(item, dict)
                ]
                if any(status in {"error", "failed"} for status in action_statuses):
                    result["status"] = "error"
                    error_messages = [
                        str((item or {}).get("message") or "").strip()
                        for item in (result.get("actions_results") or [])
                        if isinstance(item, dict) and str((item or {}).get("status") or "").strip().lower() in {"error", "failed"}
                    ]
                    if error_messages:
                        result["error"] = " | ".join(msg for msg in error_messages if msg)
                logger.info(
                    "Manifest completed | manifest_id=%s | final_status=%s | actions_results=%s",
                    str(result.get("manifest_id") or "").strip(),
                    str(result.get("status") or "").strip(),
                    _payload_preview(result.get("actions_results") or []),
                )
                
                # حفظ النتيجة في الـ Inbox
                result_path = os.path.join(inbox_dir, f"result_{os.path.basename(file_path)}")
                with open(result_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                # مسح الـ Manifest من الـ Outbox بعد التنفيذ
                if os.path.exists(file_path):
                    os.remove(file_path)
                
            except Exception as e:
                logger.error(f"Error processing manifest {file_path}: {e}")

    def _fetch_airtable_record(self, record_id, base_type="main", table_name=None, is_religious=None):
        """جلب بيانات حقل معين من Airtable للتحقق منه"""
        api_key = self.airtable_config.get("api_key")
        base_id, resolved_table_name, _ = self._resolve_airtable_target(base_type=base_type, table_name=table_name, is_religious=is_religious)
        
        if not api_key or not base_id:
            logger.error("Missing Airtable API Key or Base ID in config.")
            return None
            
        url = f"https://api.airtable.com/v0/{base_id}/{quote(resolved_table_name)}/{record_id}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch record {record_id}: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Request error while fetching {record_id}: {e}")
            return None

    def _resolve_main_booking_record_id(self, record_hint):
        record_hint = str(record_hint or "").strip()
        if not record_hint:
            return ""
        if record_hint.startswith("rec"):
            return record_hint
        api_key = self.airtable_config.get("api_key")
        base_id, resolved_table_name, _ = self._resolve_airtable_target(base_type="main")
        if not api_key or not base_id:
            logger.error("Missing Airtable API Key or Base ID in config while resolving booking record.")
            return ""
        safe_hint = record_hint.replace("'", "\\'")
        url = f"https://api.airtable.com/v0/{base_id}/{quote(resolved_table_name)}"
        headers = {"Authorization": f"Bearer {api_key}"}
        params = {
            "filterByFormula": f"{{Booking Nr.}}='{safe_hint}'",
            "maxRecords": 1,
        }
        try:
            records = self._fetch_airtable_records_paginated(url, headers, params=params)
            if records:
                return str((records[0] or {}).get("id") or "").strip()
        except Exception as e:
            logger.error(f"Failed to resolve booking number {record_hint} to Airtable record: {e}")
        return ""

    def _resolve_invoice_template_name(self, preferred_template_name=None, location=None):
        preferred = str(preferred_template_name or "").strip()
        if preferred:
            return preferred
        _ = location
        return "ftstravels_confirm_payment"

    def _build_invoice_template_variables(self, booking_fields, payment_url):
        fields = booking_fields if isinstance(booking_fields, dict) else {}
        customer_name = str(fields.get("Customer Name") or "").strip() or "Guest"
        booking_nr = str(fields.get("Booking Nr.") or "").strip() or "-"
        trip_name = str(fields.get("trip Name") or fields.get("Trip Name") or "").strip() or booking_nr
        add_ons = str(fields.get("Add - Ons") or "").strip() or "add ons"
        return [
            customer_name,
            booking_nr,
            trip_name,
            str(payment_url or "").strip(),
            trip_name,
            add_ons,
        ]

    def _update_airtable_record(self, record_id, updates, base_type="main", table_name=None, field_types=None, is_religious=None):
        """تحديث بيانات حقول Airtable مباشرة"""
        api_key = self.airtable_config.get("api_key")
        base_id, resolved_table_name, resolved_base_type = self._resolve_airtable_target(
            base_type=base_type,
            table_name=table_name,
            is_religious=is_religious,
        )
        
        if not api_key or not base_id:
            logger.error("Missing Airtable API Key or Base ID in config.")
            return False

        normalized_updates = self._normalize_airtable_update_fields(updates)
        normalized_updates = self._coerce_airtable_update_fields(normalized_updates, field_types=field_types)
        url = f"https://api.airtable.com/v0/{base_id}/{quote(resolved_table_name)}/{record_id}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {"fields": normalized_updates, "typecast": True}
        
        try:
            response = requests.patch(url, headers=headers, json=payload, timeout=20)
            if response.status_code == 200:
                logger.info(f"Successfully updated record {record_id} in {resolved_base_type}/{resolved_table_name} with {normalized_updates}")
                return True
            else:
                logger.error(f"Failed to update record {record_id}: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Request error while updating {record_id}: {e}")
            return False

    def _check_condition_flexible(self, actual_value, condition_value):
        actual = str(actual_value).strip().lower()
        cond = str(condition_value).strip().lower()
        
        if actual == cond:
            return True
            
        # مرونة في التحقق من الدفع (Paid = Succeeded = Success)
        paid_synonyms = ["paid", "succeeded", "success", "completed"]
        if actual in paid_synonyms and cond in paid_synonyms:
            return True
            
        # مرونة في التحقق من الفشل (Failed = Cancelled = Error)
        failed_synonyms = ["failed", "canceled", "cancelled", "error"]
        if actual in failed_synonyms and cond in failed_synonyms:
            return True
            
        # مرونة في التحقق من الانتظار (Pending = Waiting)
        pending_synonyms = ["pending", "waiting", "hold"]
        if actual in pending_synonyms and cond in pending_synonyms:
            return True
            
        return False

    def check_watchers(self, user_dir):
        """
        مراجعة الـ Watchers للتأكد من أي شروط متحققة بالاتصال بـ Airtable.
        """
        watchers_dir = os.path.join(user_dir, "management", "watchers")
        outbox_dir = os.path.join(user_dir, "bridge", "outbox")
        os.makedirs(watchers_dir, exist_ok=True)
        os.makedirs(outbox_dir, exist_ok=True)
        
        watcher_files = glob.glob(os.path.join(watchers_dir, "*.json"))
        for file_path in watcher_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    watcher = json.load(f)
                
                target_record = watcher.get("target_record")
                target_base = watcher.get("target_base", "main")
                condition_field = watcher.get("condition_field")
                condition_value = str(watcher.get("condition_value", "")).lower()
                
                if not target_record or not condition_field:
                    logger.warning(f"Invalid watcher in {file_path}, deleting.")
                    os.remove(file_path)
                    continue
                
                # جلب الـ Record من Airtable
                logger.info(f"Checking watcher {os.path.basename(file_path)} on record {target_record}...")
                record = self._fetch_airtable_record(target_record, target_base)
                
                if record and "fields" in record:
                    actual_value = record["fields"].get(condition_field, "")
                    
                    # التحقق من الشرط بمرونة
                    if self._check_condition_flexible(actual_value, condition_value):
                        logger.info(f"Watcher condition met for {target_record}! Triggering action...")
                        
                        # إنشاء Manifest جديد للتنفيذ
                        trigger_manifest = {
                            "manifest_id": f"man_triggered_{uuid.uuid4().hex[:8]}",
                            "intent": "watcher_triggered_execution",
                            "actions": [
                                {
                                    "type": watcher.get("action_on_trigger"),
                                    "target_record": target_record,
                                    "requires_approval": watcher.get("requires_approval", False),
                                    "payload": {"triggered_by_watcher": os.path.basename(file_path)}
                                }
                            ]
                        }
                        
                        manifest_path = os.path.join(outbox_dir, f"{trigger_manifest['manifest_id']}.json")
                        with open(manifest_path, "w", encoding="utf-8") as mf:
                            json.dump(trigger_manifest, mf, ensure_ascii=False, indent=2)
                            
                        # حذف الـ Watcher بعد تحققه
                        os.remove(file_path)
                        logger.info(f"Watcher {os.path.basename(file_path)} executed and removed.")
            
            except Exception as e:
                logger.error(f"Error evaluating watcher {file_path}: {e}")

    def check_scheduled_tasks(self, user_dir):
        """
        مراجعة المهام المجدولة لتنفيذ ما حان وقته.
        """
        tasks_dir = os.path.join(user_dir, "management", "scheduled_tasks")
        outbox_dir = os.path.join(user_dir, "bridge", "outbox")
        os.makedirs(tasks_dir, exist_ok=True)
        os.makedirs(outbox_dir, exist_ok=True)
        
        current_time = datetime.now().timestamp()
        
        task_files = glob.glob(os.path.join(tasks_dir, "*.json"))
        for file_path in task_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    task = json.load(f)
                
                execute_timestamp = task.get("execute_timestamp")
                if not execute_timestamp:
                    logger.warning(f"Task without execute_timestamp found in {file_path}, deleting.")
                    os.remove(file_path)
                    continue

                try:
                    execute_timestamp = float(execute_timestamp)
                except Exception:
                    logger.warning(f"Invalid execute_timestamp in {file_path}, deleting.")
                    os.remove(file_path)
                    continue

                pre_alert_seconds = 0
                try:
                    pre_alert_seconds = max(0, int(task.get("pre_alert_seconds") or 0))
                except Exception:
                    pre_alert_seconds = 0
                pre_alert_sent = bool(task.get("pre_alert_sent"))
                pre_alert_message = str(task.get("pre_alert_message") or "").strip()
                notify_phone = str(task.get("notify_phone") or "").strip()
                task_repeat = str(task.get("repeat") or "").strip().lower()

                if (
                    pre_alert_seconds > 0
                    and not pre_alert_sent
                    and pre_alert_message
                    and notify_phone
                    and current_time >= (execute_timestamp - pre_alert_seconds)
                    and current_time < execute_timestamp
                ):
                    if self._send_whatsapp_notification(notify_phone, pre_alert_message):
                        task["pre_alert_sent"] = True
                        task["updated_at"] = datetime.now().isoformat()
                        with open(file_path, "w", encoding="utf-8") as tf:
                            json.dump(task, tf, ensure_ascii=False, indent=2)
                
                # إذا حان وقت التنفيذ أو مر عليه
                if current_time >= execute_timestamp:
                    logger.info(f"Time reached for task {os.path.basename(file_path)}! Triggering action...")
                    
                    action_to_execute = task.get("action_to_execute", {})
                    if action_to_execute:
                        # إضافة مؤشر للمصدر
                        payload = action_to_execute.get("payload", {})
                        if isinstance(payload, dict):
                            payload["triggered_by_schedule"] = os.path.basename(file_path)
                            action_to_execute["payload"] = payload
                        
                        trigger_manifest = {
                            "manifest_id": f"man_scheduled_{uuid.uuid4().hex[:8]}",
                            "intent": "scheduled_task_execution",
                            "actions": [action_to_execute]
                        }
                        
                        manifest_path = os.path.join(outbox_dir, f"{trigger_manifest['manifest_id']}.json")
                        with open(manifest_path, "w", encoding="utf-8") as mf:
                            json.dump(trigger_manifest, mf, ensure_ascii=False, indent=2)

                    if task_repeat == "daily":
                        next_execute_timestamp = execute_timestamp + 86400
                        if next_execute_timestamp <= current_time:
                            next_execute_timestamp = current_time + 86400
                        task["execute_timestamp"] = next_execute_timestamp
                        task["pre_alert_sent"] = False
                        task["updated_at"] = datetime.now().isoformat()
                        with open(file_path, "w", encoding="utf-8") as tf:
                            json.dump(task, tf, ensure_ascii=False, indent=2)
                        logger.info(f"Scheduled task {os.path.basename(file_path)} repeated for next day.")
                    else:
                        # مسح المهمة المجدولة بعد إرسالها للتنفيذ
                        os.remove(file_path)
                        logger.info(f"Scheduled task {os.path.basename(file_path)} sent to outbox and removed.")
            
            except Exception as e:
                logger.error(f"Error evaluating scheduled task {file_path}: {e}")

    def _run_loop(self):
        logger.info("Background Task Engine started.")
        while self.is_running:
            for user_dir in self._get_user_dirs():
                self.process_outbox(user_dir)
                self.check_watchers(user_dir)
                self.check_scheduled_tasks(user_dir)
                
                # Scan Inbox to learn from recent execution results
                user_key = os.path.basename(user_dir)
                self.knowledge_engine.process_inbox_feedback(user_key)
            
            time.sleep(self.check_interval)

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.is_running = False
        if hasattr(self, 'thread'):
            self.thread.join()
        logger.info("Background Task Engine stopped.")

# للتجربة السريعة أو التشغيل المباشر
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    engine = BackgroundTaskEngine(check_interval=10) # فحص كل 10 ثواني
    
    try:
        logger.info("Starting PI Background Task Engine. Press Ctrl+C to stop.")
        engine.start()
        # ابق المحرك يعمل
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping PI Background Task Engine...")
        engine.stop()
