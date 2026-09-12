import hashlib
import json
import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timedelta

import requests

import automation_db

VISUAL_KEYWORD_DEDUP_WINDOW_SECONDS = 600
_NON_TEXT_MEDIA_PREFIXES = (
    "[customer sent an audio message.",
    "[customer sent a video.",
    "[customer sent a sticker.",
    "[customer sent a document.",
    "[customer sent a message of type:",
    "[customer shared a location]",
    "[customer shared contacts.",
)


def _utc_now():
    return datetime.utcnow().isoformat()


def _get_by_path(obj, path: str):
    if not path:
        return None
    cur = obj
    for part in str(path).split("."):
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, (list, tuple)):
            try:
                idx = int(part)
            except Exception:
                return None
            if idx < 0 or idx >= len(cur):
                return None
            cur = cur[idx]
        else:
            try:
                cur = getattr(cur, part)
            except Exception:
                return None
    return cur


_TPL_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_\.\-]+)\s*\}\}")


def _render_template(text: str, ctx: dict):
    s = str(text or "")
    if not s:
        return s

    def _rep(m):
        key = m.group(1)
        val = _get_by_path(ctx, key)
        if val is None:
            return ""
        if isinstance(val, (dict, list)):
            try:
                return json.dumps(val, ensure_ascii=False)
            except Exception:
                return str(val)
        return str(val)

    return _TPL_RE.sub(_rep, s)


def normalize_keyword_text(text: str) -> str:
    """Same normalization as knowledge_base._normalize_rule_text / religious keyword workflows."""
    try:
        s = str(text or "").strip().lower()
        s = re.sub(r"[\u0610-\u061A\u0640\u064B-\u065F\u0670\u06D6-\u06ED]", "", s)
        s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
        s = re.sub(r"\s+", " ", s, flags=re.UNICODE)
        return s.strip()
    except Exception:
        return str(text or "").strip().lower()


def is_non_text_media_message(message_body: str) -> bool:
    lb = str(message_body or "").lower().strip()
    return any(lb.startswith(p) for p in _NON_TEXT_MEDIA_PREFIXES)


def keyword_matches(message_body: str, keywords, match_mode: str = "phrase"):
    """
    Return the first matching keyword, or None.

    Modes:
      exact    — normalized message == normalized keyword
      phrase   — exact, OR the raw keyword (including emoji) appears in the raw message
      contains — normalized keyword is contained in the normalized message
    """
    raw_message = str(message_body or "").strip()
    normalized_message = normalize_keyword_text(raw_message)
    if not normalized_message and not raw_message:
        return None
    mode = str(match_mode or "phrase").strip().lower()
    if mode in ("literal", "in_message", "phrase_in_message"):
        mode = "phrase"
    if isinstance(keywords, str):
        items = [keywords]
    elif isinstance(keywords, (list, tuple)):
        items = list(keywords)
    else:
        items = []
    for raw_kw in items:
        keyword = str(raw_kw or "").strip()
        if not keyword:
            continue
        normalized_keyword = normalize_keyword_text(keyword)
        if mode == "exact":
            if normalized_keyword and normalized_message == normalized_keyword:
                return keyword
        elif mode == "contains":
            if normalized_keyword and normalized_keyword in normalized_message:
                return keyword
            if keyword and keyword in raw_message:
                return keyword
        else:
            # phrase (default): exact after normalize, or the literal keyword in the raw text
            if normalized_keyword and normalized_message == normalized_keyword:
                return keyword
            if keyword and keyword in raw_message:
                return keyword
    return None


def _visual_dedup_db_path() -> str:
    try:
        from fts_paths import get_data_path
        return get_data_path("visual_keyword_reply_dedup.db")
    except Exception:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "visual_keyword_reply_dedup.db")


def collect_keyword_media(step: dict):
    """Normalize visual-builder attachments from step JSON."""
    if not isinstance(step, dict):
        return []
    raw = step.get("media") or step.get("attachments") or []
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        raw = []
    single_url = str(step.get("media_url") or "").strip()
    if single_url:
        raw = [{
            "url": single_url,
            "media_type": step.get("media_type") or step.get("mediaType") or "document",
            "filename": step.get("media_filename") or step.get("filename") or "",
            "mime": step.get("media_mime") or step.get("mime") or "",
        }] + list(raw)
    items = []
    seen = set()
    for item in raw:
        if isinstance(item, str):
            url = item.strip()
            filename = ""
            media_type = "image"
            mime = ""
        elif isinstance(item, dict):
            url = str(item.get("url") or item.get("media_url") or "").strip()
            filename = str(item.get("filename") or item.get("name") or "").strip()
            media_type = str(item.get("media_type") or item.get("mediaType") or "").strip().lower()
            mime = str(item.get("mime") or item.get("media_mime") or "").strip()
        else:
            continue
        if not url or url in seen:
            continue
        seen.add(url)
        if not media_type:
            name = (filename or url).lower()
            mime_l = mime.lower()
            if mime_l.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")):
                media_type = "image"
            elif mime_l.startswith("video/") or name.endswith((".mp4", ".mov", ".webm")):
                media_type = "video"
            elif mime_l.startswith("audio/") or name.endswith((".mp3", ".m4a", ".ogg", ".opus", ".webm")):
                media_type = "audio"
            else:
                media_type = "document"
        items.append({
            "url": url,
            "media_type": media_type,
            "filename": filename,
            "mime": mime,
        })
        if len(items) >= 8:
            break
    return items


def claim_visual_keyword_reply(workflow_id: str, chat_id: str, message_body: str) -> bool:
    """Atomic per-workflow claim so webhook duplicates do not send twice."""
    try:
        normalized = normalize_keyword_text(message_body)
        body_hash = hashlib.sha256(normalized.encode("utf-8", errors="ignore")).hexdigest()[:24]
    except Exception:
        body_hash = "0" * 24
    unified_key = f"{str(workflow_id or '').strip()}:{str(chat_id or '').strip()}:{body_hash}"
    now = datetime.utcnow().isoformat()
    db_path = _visual_dedup_db_path()
    try:
        with sqlite3.connect(db_path, timeout=30.0) as conn:
            conn.execute("PRAGMA busy_timeout = 30000;")
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS visual_keyword_reply_dedup (
                    dedup_key TEXT PRIMARY KEY,
                    workflow_id TEXT,
                    chat_id TEXT NOT NULL,
                    replied_at TEXT NOT NULL
                )
                """
            )
            try:
                cutoff = (datetime.utcnow() - timedelta(seconds=VISUAL_KEYWORD_DEDUP_WINDOW_SECONDS)).isoformat()
                cur.execute("DELETE FROM visual_keyword_reply_dedup WHERE replied_at < ?", (cutoff,))
            except Exception:
                pass
            cur.execute(
                "INSERT OR IGNORE INTO visual_keyword_reply_dedup (dedup_key, workflow_id, chat_id, replied_at) VALUES (?, ?, ?, ?)",
                (unified_key, str(workflow_id or ""), str(chat_id or ""), now),
            )
            conn.commit()
            return cur.rowcount > 0
    except Exception:
        return True


class StopWorkflow(Exception):
    pass


class AutomationEngine:
    def __init__(self, agent):
        self.agent = agent
        self._schedule_state = {}
        self._lock = threading.Lock()
        self._tick_last = 0.0
        # Make-like Run once for webhooks: token -> wait session
        self._run_once_waits = {}

    def arm_run_once_wait(self, workflow_id: str, token: str, timeout_seconds: int = 90) -> dict:
        """Arm one-shot wait for the next webhook POST (Make Run once → Waiting for data)."""
        tok = automation_db.normalize_webhook_public_token(token)
        wid = str(workflow_id or "").strip()
        if not tok or not wid:
            return {"ok": False, "error": "missing_token_or_workflow"}
        timeout_seconds = max(15, min(int(timeout_seconds or 90), 300))
        now = time.time()
        with self._lock:
            # Clear expired sessions
            dead = []
            for k, v in self._run_once_waits.items():
                if not isinstance(v, dict):
                    dead.append(k)
                    continue
                if float(v.get("expires_at") or 0) < now and str(v.get("status") or "") == "waiting":
                    v["status"] = "timeout"
                    v["logs"] = list(v.get("logs") or []) + [
                        {"t": _utc_now(), "msg": "Exceeded maximum wait time."}
                    ]
                if str(v.get("status") or "") in ("timeout", "stopped", "completed") and float(v.get("expires_at") or 0) < now - 120:
                    dead.append(k)
            for k in dead:
                self._run_once_waits.pop(k, None)

            session = {
                "workflow_id": wid,
                "token": tok,
                "status": "waiting",
                "created_at": now,
                "expires_at": now + timeout_seconds,
                "timeout_seconds": timeout_seconds,
                "result": None,
                "payload": None,
                "logs": [
                    {"t": _utc_now(), "msg": "Preparing scenario for running."},
                    {"t": _utc_now(), "msg": "Requesting execution."},
                    {"t": _utc_now(), "msg": "The request was accepted. Waiting for data."},
                ],
            }
            self._run_once_waits[tok] = session
            return {
                "ok": True,
                "status": "waiting",
                "token": tok,
                "workflow_id": wid,
                "timeout_seconds": timeout_seconds,
                "logs": session["logs"],
            }

    def stop_run_once_wait(self, workflow_id: str = "", token: str = "") -> dict:
        tok = automation_db.normalize_webhook_public_token(token)
        wid = str(workflow_id or "").strip()
        with self._lock:
            session = None
            if tok and tok in self._run_once_waits:
                session = self._run_once_waits.get(tok)
            elif wid:
                for k, v in self._run_once_waits.items():
                    if isinstance(v, dict) and str(v.get("workflow_id") or "") == wid and str(v.get("status") or "") == "waiting":
                        session = v
                        tok = k
                        break
            if not session:
                return {"ok": True, "status": "idle"}
            if str(session.get("status") or "") == "waiting":
                session["status"] = "stopped"
                session["logs"] = list(session.get("logs") or []) + [
                    {"t": _utc_now(), "msg": "Scenario was stopped."}
                ]
            return {
                "ok": True,
                "status": str(session.get("status") or "stopped"),
                "logs": list(session.get("logs") or []),
                "token": tok,
            }

    def get_run_once_wait(self, workflow_id: str = "", token: str = "") -> dict:
        tok = automation_db.normalize_webhook_public_token(token)
        wid = str(workflow_id or "").strip()
        now = time.time()
        with self._lock:
            session = None
            if tok and tok in self._run_once_waits:
                session = self._run_once_waits.get(tok)
            elif wid:
                for k, v in self._run_once_waits.items():
                    if isinstance(v, dict) and str(v.get("workflow_id") or "") == wid:
                        session = v
                        tok = k
                        break
            if not session:
                return {"ok": True, "status": "idle", "logs": []}
            if str(session.get("status") or "") == "waiting" and float(session.get("expires_at") or 0) < now:
                session["status"] = "timeout"
                session["logs"] = list(session.get("logs") or []) + [
                    {"t": _utc_now(), "msg": "Exceeded maximum wait time."}
                ]
            return {
                "ok": True,
                "status": str(session.get("status") or "idle"),
                "token": tok,
                "workflow_id": str(session.get("workflow_id") or ""),
                "logs": list(session.get("logs") or []),
                "result": session.get("result"),
                "operations": (session.get("result") or {}).get("operations")
                if isinstance(session.get("result"), dict)
                else [],
            }

    def consume_run_once_wait_if_armed(self, token: str, payload: dict = None):
        """
        If Run once is waiting for this webhook token, run the workflow once and
        complete the wait session (works even when the scenario is Inactive — like Make).
        Returns (handled: bool, response_dict_or_None).
        """
        tok = automation_db.normalize_webhook_public_token(token)
        if not tok:
            return False, None
        with self._lock:
            session = self._run_once_waits.get(tok)
            if not session or str(session.get("status") or "") != "waiting":
                return False, None
            now = time.time()
            if float(session.get("expires_at") or 0) < now:
                session["status"] = "timeout"
                session["logs"] = list(session.get("logs") or []) + [
                    {"t": _utc_now(), "msg": "Exceeded maximum wait time."}
                ]
                return True, {
                    "ok": False,
                    "error": "wait_timeout",
                    "status": "timeout",
                }
            # Claim the wait so duplicate POSTs don't double-run
            session["status"] = "running"
            session["logs"] = list(session.get("logs") or []) + [
                {"t": _utc_now(), "msg": "The scenario was initialized."}
            ]
            wid = str(session.get("workflow_id") or "")

        try:
            res = self.run_manual(wid, payload=payload or {})
        except Exception as e:
            with self._lock:
                session = self._run_once_waits.get(tok) or {}
                session["status"] = "error"
                session["result"] = {"ok": False, "error": str(e)}
                session["logs"] = list(session.get("logs") or []) + [
                    {"t": _utc_now(), "msg": f"The scenario run failed: {e}"},
                ]
                self._run_once_waits[tok] = session
            return True, {"ok": False, "error": str(e), "status": "error"}

        with self._lock:
            session = self._run_once_waits.get(tok) or {}
            session["status"] = "completed"
            session["payload"] = payload or {}
            session["result"] = res if isinstance(res, dict) else {"ok": True, "raw": res}
            session["logs"] = list(session.get("logs") or []) + [
                {"t": _utc_now(), "msg": "The scenario was finalized."},
                {"t": _utc_now(), "msg": "The scenario run was completed."},
            ]
            self._run_once_waits[tok] = session
        return True, {
            "ok": True,
            "status": "completed",
            "result": session.get("result"),
            "operations": (session.get("result") or {}).get("operations")
            if isinstance(session.get("result"), dict)
            else [],
        }

    def emit_message_received(self, payload: dict):
        try:
            threading.Thread(
                target=self._handle_event,
                args=("message_received", payload or {}),
                daemon=True,
            ).start()
        except Exception:
            return

    def handle_message_received_sync(self, payload: dict):
        """
        Run message_received workflows to completion on the current thread.
        Required for Religious/draft locations so keyword autoreply can finish
        before the AI path decides to insert a [PROPOSED_DRAFT].

        Returns {"ok": True, "sent": bool} so callers can skip AI drafts when a
        keyword workflow already sent a live reply.
        """
        try:
            return self._handle_event("message_received", payload or {}) or {"ok": True, "sent": False}
        except Exception:
            return {"ok": False, "sent": False}

    def run_manual(self, workflow_id: str, payload: dict = None):
        return self._run_workflow_by_id(workflow_id, event_type="manual", event_payload=payload or {})

    def tick(self):
        now = time.time()
        with self._lock:
            if self._tick_last and (now - self._tick_last) < 10:
                return
            self._tick_last = now
        self._run_schedules()

    def _run_schedules(self):
        try:
            workflows = automation_db.list_workflows()
        except Exception:
            workflows = []

        for wf in workflows:
            try:
                if int(wf.get("enabled") or 0) != 1:
                    continue
                if str(wf.get("trigger_type") or "").strip().lower() != "schedule":
                    continue
                trigger_cfg = {}
                try:
                    trigger_cfg = json.loads(str(wf.get("trigger_config_json") or "{}"))
                    if not isinstance(trigger_cfg, dict):
                        trigger_cfg = {}
                except Exception:
                    trigger_cfg = {}

                every_seconds = trigger_cfg.get("every_seconds")
                every_minutes = trigger_cfg.get("every_minutes")
                every_hours = trigger_cfg.get("every_hours")
                interval = None
                if every_seconds is not None:
                    try:
                        interval = float(every_seconds)
                    except Exception:
                        interval = None
                elif every_minutes is not None:
                    try:
                        interval = float(every_minutes) * 60.0
                    except Exception:
                        interval = None
                elif every_hours is not None:
                    try:
                        interval = float(every_hours) * 3600.0
                    except Exception:
                        interval = None

                if not interval or interval <= 0:
                    continue

                wid = str(wf.get("id") or "")
                st = self._schedule_state.get(wid) or {}
                last_ts = float(st.get("last_ts") or 0.0)
                if last_ts and (time.time() - last_ts) < interval:
                    continue
                # Prevent overlapping concurrent runs of the same scheduled workflow
                if bool(st.get("running")):
                    continue

                self._schedule_state[wid] = {"last_ts": time.time(), "running": True}

                def _runner(_wid=wid):
                    try:
                        self._run_workflow_by_id(
                            _wid,
                            event_type="schedule",
                            event_payload={"trigger": trigger_cfg},
                        )
                    finally:
                        cur = self._schedule_state.get(_wid) or {}
                        cur["running"] = False
                        cur["last_ts"] = time.time()
                        self._schedule_state[_wid] = cur

                threading.Thread(target=_runner, daemon=True).start()
            except Exception:
                continue

    def _handle_event(self, event_type: str, payload: dict):
        any_sent = False
        try:
            workflows = automation_db.list_workflows()
        except Exception:
            workflows = []

        event_company = ""
        try:
            event_company = automation_db.normalize_workflow_company_id(
                (payload or {}).get("company_id") or (payload or {}).get("companyId") or ""
            )
            # Empty payload company means "unknown" — do not default to fts here or we
            # would skip non-FTS workflows incorrectly. Only filter when explicitly set.
            raw_cid = str((payload or {}).get("company_id") or (payload or {}).get("companyId") or "").strip()
            if not raw_cid:
                event_company = ""
        except Exception:
            event_company = ""

        for wf in workflows:
            try:
                if int(wf.get("enabled") or 0) != 1:
                    continue
                if str(wf.get("trigger_type") or "").strip().lower() != str(event_type or "").strip().lower():
                    continue

                if event_company:
                    try:
                        if automation_db.workflow_company_id(wf) != event_company:
                            continue
                    except Exception:
                        pass

                trigger_cfg = {}
                try:
                    trigger_cfg = json.loads(str(wf.get("trigger_config_json") or "{}"))
                    if not isinstance(trigger_cfg, dict):
                        trigger_cfg = {}
                except Exception:
                    trigger_cfg = {}

                if event_type == "message_received":
                    want_source = str(trigger_cfg.get("source") or "Any").strip().lower()
                    src = str(payload.get("source") or "").strip().lower()
                    if want_source not in ["any", "*", "all", ""]:
                        if src != want_source:
                            continue

                result = self._run_workflow(wf, event_type=event_type, event_payload=payload)
                if isinstance(result, dict) and result.get("sent"):
                    any_sent = True
            except Exception:
                continue
        return {"ok": True, "sent": any_sent}

    def _run_workflow_by_id(self, workflow_id: str, event_type: str = None, event_payload: dict = None):
        wf = None
        try:
            wf = automation_db.get_workflow(workflow_id)
        except Exception:
            wf = None
        if not wf:
            return {"ok": False, "error": "not_found"}
        return self._run_workflow(wf, event_type=event_type or "manual", event_payload=event_payload or {})

    def _run_workflow(self, wf: dict, event_type: str, event_payload: dict):
        wid = str(wf.get("id") or "").strip()
        # #region debug-point A:workflow-run-entry
        try:
            import json as _dbg_json, urllib.request as _dbg_req; _p='.dbg/duplicate-pickup-send.env'; _u,_s='http://127.0.0.1:7777/event','duplicate-pickup-send'; exec("try:\n with open(_p, encoding='utf-8') as f: c=f.read(); _u=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SERVER_URL=')),_u); _s=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SESSION_ID=')),_s)\nexcept: pass"); _dbg_req.urlopen(_dbg_req.Request(_u, data=_dbg_json.dumps({'sessionId':_s,'runId':'pre-fix','hypothesisId':'A','location':'automation_engine.py:198','msg':'[DEBUG] workflow run entry','data':{'workflow_id':wid,'workflow_name':str(wf.get('name') or ''),'event_type':event_type,'event_payload':event_payload or {}}}, separators=(',', ':')).encode(), headers={'Content-Type':'application/json'}), timeout=0.25).read()
        except Exception:
            pass
        # #endregion
        run_id = None
        try:
            run_id = automation_db.create_run(wid, event_type, event_payload or {})
        except Exception:
            run_id = None

        try:
            run_company_id = automation_db.workflow_company_id(wf)
        except Exception:
            run_company_id = ""
        ctx = {
            "now": _utc_now(),
            "event": {"type": event_type, "payload": event_payload or {}},
            "vars": {},
            "workflow": {"id": wid, "name": str(wf.get("name") or wid).strip()},
            "company_id": run_company_id,
        }

        chat_id = str((event_payload or {}).get("chat_id") or "").strip()
        if chat_id:
            try:
                import chat_db

                ctx["chat"] = chat_db.get_conversation(chat_id) or {}
            except Exception:
                ctx["chat"] = {}

        try:
            steps = json.loads(str(wf.get("steps_json") or "[]"))
            if not isinstance(steps, list):
                steps = []
        except Exception:
            steps = []

        err = None
        ctx["_exec_ops"] = []
        try:
            tcfg = {}
            try:
                raw_tcfg = wf.get("trigger_config")
                if isinstance(raw_tcfg, dict):
                    tcfg = raw_tcfg
                else:
                    tcfg = json.loads(str(wf.get("trigger_config_json") or "{}"))
                if not isinstance(tcfg, dict):
                    tcfg = {}
            except Exception:
                tcfg = {}
            self._record_operation(
                ctx,
                {
                    "type": "trigger",
                    "_canvas_node_id": tcfg.get("_canvas_node_id"),
                    "_module_id": tcfg.get("_module_id"),
                    "_label": tcfg.get("_label"),
                    "trigger_type": event_type,
                },
                output={"type": event_type, "payload": event_payload or {}},
                status="success",
            )
        except Exception:
            pass

        try:
            for step in steps:
                if not isinstance(step, dict):
                    continue
                self._dispatch_step(step, ctx)
            try:
                automation_db.touch_run_success(wid)
            except Exception:
                pass
        except StopWorkflow:
            err = None
            try:
                automation_db.touch_run_success(wid)
            except Exception:
                pass
        except Exception as e:
            err = str(e)
            try:
                automation_db.touch_run_error(wid, err)
            except Exception:
                pass
        finally:
            if run_id:
                try:
                    final_payload = event_payload.copy() if isinstance(event_payload, dict) else {}
                    if ctx.get("vars"):
                        final_payload["result"] = ctx["vars"]
                    if ctx.get("_exec_ops"):
                        final_payload["operations"] = ctx.get("_exec_ops")
                    automation_db.finish_run(run_id, "success" if not err else "error", error=err, payload=final_payload)
                except Exception:
                    pass
        sent = bool((ctx.get("vars") or {}).get("_workflow_sent"))
        return {
            "ok": err is None,
            "error": err,
            "sent": sent,
            "operations": list(ctx.get("_exec_ops") or []),
        }

    def _json_size_bytes(self, value) -> int:
        try:
            return len(json.dumps(value, ensure_ascii=False, default=str).encode("utf-8"))
        except Exception:
            try:
                return len(str(value).encode("utf-8"))
            except Exception:
                return 0

    def _safe_clone(self, value, depth: int = 0):
        if depth > 6:
            return str(value)[:200]
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, dict):
            out = {}
            for i, (k, v) in enumerate(value.items()):
                if i >= 40:
                    out["…"] = f"+{len(value) - 40} keys"
                    break
                sk = str(k)
                if any(x in sk.lower() for x in ("token", "password", "secret", "api_key", "authorization")):
                    out[sk] = "***"
                else:
                    out[sk] = self._safe_clone(v, depth + 1)
            return out
        if isinstance(value, (list, tuple)):
            return [self._safe_clone(v, depth + 1) for v in list(value)[:40]]
        return str(value)[:300]

    def _record_operation(self, ctx: dict, step: dict, output=None, status: str = "success", error: str = None):
        try:
            ops = ctx.get("_exec_ops")
            if not isinstance(ops, list):
                ops = []
                ctx["_exec_ops"] = ops
            out = self._safe_clone(output if output is not None else {})
            op = {
                "index": len(ops) + 1,
                "nodeId": str(step.get("_canvas_node_id") or "").strip() or None,
                "moduleId": str(step.get("_module_id") or "").strip() or None,
                "label": str(step.get("_label") or "").strip() or None,
                "stepType": str(step.get("type") or "").strip().lower(),
                "status": status,
                "bytes": self._json_size_bytes(out),
                "output": out,
            }
            if error:
                op["error"] = str(error)[:500]
            ops.append(op)
        except Exception:
            pass

    def _build_step_output(self, stype: str, step: dict, ctx: dict):
        stype = str(stype or "").lower()
        vars_map = ctx.get("vars") if isinstance(ctx.get("vars"), dict) else {}
        if stype == "http_request":
            out = {
                "type": "http_request",
                "method": step.get("method") or "POST",
                "url": step.get("url") or "",
                "headers": step.get("headers") if isinstance(step.get("headers"), dict) else {},
                "timeout_seconds": step.get("timeout_seconds") or 30,
                "body": step.get("body"),
            }
            ok = str(step.get("output_key") or "").strip()
            if ok and ok in vars_map:
                out["response"] = vars_map.get(ok)
            return out
        if stype == "guard":
            return {"type": "guard", "path": step.get("path"), "passed": True}
        if stype == "router":
            return {
                "type": "router",
                "route": vars_map.get("_router_route"),
                "label": vars_map.get("_router_label"),
                "mode": step.get("mode") or "first_match",
            }
        if stype in ("send_whatsapp", "send_email", "send_internal_notification"):
            last = vars_map.get("_last_whatsapp_send") if stype == "send_whatsapp" else None
            if isinstance(last, dict):
                return {
                    "type": stype,
                    "to": last.get("to") or step.get("to"),
                    "mode": last.get("mode"),
                    "template_name": last.get("template_name"),
                    "template_language": last.get("template_language"),
                    "text": last.get("text") or step.get("text") or step.get("html") or step.get("message"),
                    "subject": step.get("subject"),
                    "location": last.get("location"),
                    "receiving_phone_id": last.get("receiving_phone_id"),
                }
            return {
                "type": stype,
                "to": step.get("to"),
                "text": step.get("text") or step.get("html") or step.get("message"),
                "subject": step.get("subject"),
                "message_mode": step.get("message_mode"),
                "template_name": step.get("template_name"),
            }
        if stype == "set_variable":
            key = str(step.get("key") or "value")
            return {"type": "set_variable", "key": key, "value": vars_map.get(key)}
        if stype in ("text_parser", "json_parse", "ai"):
            ok = str(
                step.get("output_key")
                or ("parsed" if stype == "text_parser" else "json" if stype == "json_parse" else "ai")
            )
            return {"type": stype, "output_key": ok, "value": vars_map.get(ok)}
        if stype == "sleep":
            return {"type": "sleep", "seconds": step.get("seconds") or 1}
        return {"type": stype or "step", "vars": self._safe_clone(vars_map)}

    def _dispatch_step(self, step: dict, ctx: dict):
        stype = str(step.get("type") or "").strip().lower()
        if not stype:
            return
        try:
            if stype == "guard":
                self._step_guard(step, ctx)
            elif stype == "router":
                self._step_router(step, ctx)
            elif stype == "ai":
                self._step_ai(step, ctx)
            elif stype == "airtable_update":
                self._step_airtable_update(step, ctx)
            elif stype == "send_whatsapp":
                self._step_send_whatsapp(step, ctx)
            elif stype == "send_email":
                self._step_send_email(step, ctx)
            elif stype == "http_request":
                self._step_http_request(step, ctx)
            elif stype == "send_internal_notification":
                self._step_send_internal_notification(step, ctx)
            elif stype in ("keyword_reply", "visual_keyword_reply"):
                self._step_keyword_reply(step, ctx)
            elif stype == "set_variable":
                self._step_set_variable(step, ctx)
            elif stype == "text_parser":
                self._step_text_parser(step, ctx)
            elif stype == "json_parse":
                self._step_json_parse(step, ctx)
            elif stype == "sleep":
                self._step_sleep(step, ctx)
            else:
                return
            self._record_operation(ctx, step, output=self._build_step_output(stype, step, ctx), status="success")
        except StopWorkflow as sw:
            self._record_operation(
                ctx,
                step,
                output={"type": stype, "stopped": True, "reason": str(sw)},
                status="stopped",
                error=str(sw),
            )
            raise
        except Exception as e:
            self._record_operation(ctx, step, output={"type": stype}, status="error", error=str(e))
            raise

    def _eval_router_filter(self, filt, ctx: dict) -> bool:
        """Make-like route filter. None/empty filter = always match (fallback)."""
        if filt is None:
            return True
        if not isinstance(filt, dict):
            return True
        path = str(filt.get("field") or filt.get("path") or "event.payload.message_body").strip()
        op = str(filt.get("op") or "contains").strip().lower()
        raw_val = _get_by_path(ctx, path)
        s = "" if raw_val is None else str(raw_val)
        ci = filt.get("case_insensitive")
        ci = True if ci is None else bool(ci)
        needle = "" if filt.get("value") is None else str(filt.get("value"))
        hay = s.lower() if ci else s
        nd = needle.lower() if ci else needle

        if op in ("empty", "is_empty"):
            return not s.strip()
        if op in ("nonempty", "not_empty", "exists"):
            return bool(s.strip())
        if op in ("eq", "equals", "=="):
            return hay == nd
        if op == "regex":
            if not needle.strip():
                return True
            flags = re.IGNORECASE if ci else 0
            return bool(re.search(needle, s, flags))
        # default: contains
        if not nd:
            return True
        return nd in hay

    def _step_router(self, step: dict, ctx: dict):
        routes = step.get("routes")
        if not isinstance(routes, list):
            routes = []
        mode = str(step.get("mode") or "first_match").strip().lower()
        matched_any = False
        for route in routes:
            if not isinstance(route, dict):
                continue
            filt = route.get("filter", None)
            if filt == "":
                filt = None
            if not self._eval_router_filter(filt, ctx):
                continue
            matched_any = True
            route_id = str(route.get("id") or "").strip()
            route_label = str(route.get("label") or route_id).strip()
            try:
                if not isinstance(ctx.get("vars"), dict):
                    ctx["vars"] = {}
                ctx["vars"]["_router_route"] = route_id
                ctx["vars"]["_router_label"] = route_label
            except Exception:
                pass
            nested = route.get("steps")
            if isinstance(nested, list):
                for nested_step in nested:
                    if isinstance(nested_step, dict):
                        self._dispatch_step(nested_step, ctx)
            if mode != "all_matching":
                return
        if not matched_any:
            raise StopWorkflow("router_no_match")

    def _is_human_active_chat(self, chat_id: str) -> bool:
        try:
            import chat_db
            conv = chat_db.get_conversation(chat_id) or {}
            return int(conv.get("needs_help") or 0) == 1
        except Exception:
            return False

    def _is_chat_on_hold(self, chat_id: str) -> bool:
        try:
            import chat_db
            conv = chat_db.get_conversation(chat_id) or {}
            hold_raw = str(conv.get("auto_reply_hold_until") or "").strip()
            if not hold_raw:
                return False
            try:
                now = datetime.fromisoformat(chat_db.get_cairo_time())
                if now.tzinfo is not None:
                    now = now.replace(tzinfo=None)
                hold_dt = datetime.fromisoformat(hold_raw)
                if hold_dt.tzinfo is not None:
                    hold_dt = hold_dt.replace(tzinfo=None)
                if hold_dt > now:
                    return True
                try:
                    chat_db.update_auto_reply_hold_until(chat_id, None)
                except Exception:
                    pass
            except Exception:
                return False
        except Exception:
            return False
        return False

    def _step_keyword_reply(self, step: dict, ctx: dict):
        """
        Visual builder step: match a customer keyword and send a fixed reply
        on WhatsApp or Facebook without generating a Python workflow file.
        """
        payload = _get_by_path(ctx, "event.payload") or {}
        if not isinstance(payload, dict):
            payload = {}
        chat_id = str(payload.get("chat_id") or "").strip()
        message_body = str(payload.get("message_body") or "").strip()
        source = str(payload.get("source") or "").strip().lower()
        sender_identifier = str(payload.get("sender_identifier") or "").strip()
        location = str(payload.get("location") or "").strip()
        receiving_phone_id = str(payload.get("receiving_phone_id") or "").strip() or None

        want_location = str(step.get("location") or "Religious").strip() or "Religious"
        if want_location.lower() not in location.lower():
            raise StopWorkflow("keyword_reply_wrong_location")

        sources = step.get("sources")
        if isinstance(sources, str):
            allowed_sources = [sources.strip().lower()] if sources.strip() else []
        elif isinstance(sources, (list, tuple)):
            allowed_sources = [str(x or "").strip().lower() for x in sources if str(x or "").strip()]
        else:
            allowed_sources = ["facebook", "whatsapp"]
        if allowed_sources and source not in allowed_sources:
            raise StopWorkflow("keyword_reply_unsupported_source")

        if not chat_id or not message_body or not sender_identifier:
            raise StopWorkflow("keyword_reply_missing_data")

        skip_media = True if step.get("skip_media") is None else bool(step.get("skip_media"))
        if skip_media and is_non_text_media_message(message_body):
            raise StopWorkflow("keyword_reply_non_text_media")

        skip_if_hold = True if step.get("skip_if_hold") is None else bool(step.get("skip_if_hold"))
        if skip_if_hold and self._is_chat_on_hold(chat_id):
            raise StopWorkflow("keyword_reply_human_hold")

        skip_if_human = True if step.get("skip_if_human") is None else bool(step.get("skip_if_human"))
        if skip_if_human and self._is_human_active_chat(chat_id):
            raise StopWorkflow("keyword_reply_human_active")

        matched = keyword_matches(
            message_body,
            step.get("keywords") or step.get("keyword"),
            match_mode=str(step.get("match_mode") or "phrase"),
        )
        if not matched:
            raise StopWorkflow("keyword_reply_no_match")

        reply = _render_template(str(step.get("reply") or step.get("text") or ""), ctx).strip()
        media_items = collect_keyword_media(step)
        if not reply and not media_items:
            raise StopWorkflow("keyword_reply_empty_reply")

        wf = ctx.get("workflow") if isinstance(ctx.get("workflow"), dict) else {}
        workflow_id = str(wf.get("id") or "").strip()
        if not claim_visual_keyword_reply(workflow_id, chat_id, message_body):
            raise StopWorkflow("keyword_reply_already_processed")

        use_whatsapp = source == "whatsapp" or str(sender_identifier).startswith("20")
        channel = "WhatsApp" if use_whatsapp else "Facebook"
        if not self.agent:
            raise Exception("keyword_reply_missing_agent")
        try:
            ok, error = self._send_keyword_reply_payload(
                use_whatsapp=use_whatsapp,
                sender_identifier=sender_identifier,
                reply=reply,
                media_items=media_items,
                location=location or "Religious",
                receiving_phone_id=receiving_phone_id,
            )
        except Exception as e:
            raise Exception(f"keyword_reply_send_failed:{e}")
        if not ok:
            raise Exception(f"keyword_reply_send_failed:{error}")

        log_text = reply
        for att in media_items:
            line = f"[Sent {str(att.get('media_type') or 'attachment').capitalize()}] {att.get('url') or att.get('filename') or 'attachment'}"
            log_text = f"{line}\n{log_text}".strip() if log_text else line
        try:
            import chat_db
            chat_db.add_message(
                chat_id=chat_id,
                sender_type="agent",
                text=log_text or reply,
                status="sent",
                source=channel,
            )
            try:
                chat_db.mark_conversation_read(chat_id)
            except Exception:
                pass
            try:
                chat_db.delete_proposed_drafts(chat_id)
            except Exception:
                pass
        except Exception:
            pass
        try:
            if hasattr(self.agent, "cancel_whatsapp_ai_processing"):
                self.agent.cancel_whatsapp_ai_processing(
                    chat_id=chat_id,
                    reason="visual_keyword_reply",
                )
        except Exception:
            pass
        try:
            if hasattr(self.agent, "mark_workflow_live_reply"):
                self.agent.mark_workflow_live_reply(chat_id, reason="visual_keyword_reply")
        except Exception:
            pass

        ctx.setdefault("vars", {})
        ctx["vars"]["_workflow_sent"] = True
        ctx["vars"]["keyword_reply"] = {
            "sent": True,
            "chat_id": chat_id,
            "keyword": matched,
            "channel": channel,
            "media_count": len(media_items),
        }

    def _send_keyword_reply_payload(
        self,
        use_whatsapp: bool,
        sender_identifier: str,
        reply: str,
        media_items: list,
        location: str,
        receiving_phone_id,
    ):
        """Send text and/or attachments on WhatsApp or Facebook."""
        media_items = [m for m in (media_items or []) if isinstance(m, dict) and str(m.get("url") or "").strip()]
        last_error = None

        if use_whatsapp:
            if media_items:
                long_caption = bool(reply) and len(reply) > 1024
                if long_caption:
                    ok, last_error = self.agent.send_whatsapp_message(
                        sender_identifier,
                        text=reply,
                        location=location,
                        receiving_phone_id=receiving_phone_id,
                    )
                    if not ok:
                        return False, last_error
                    reply_for_caption = ""
                else:
                    reply_for_caption = reply
                for i, att in enumerate(media_items):
                    caption = reply_for_caption if i == 0 else ""
                    ok, last_error = self.agent.send_whatsapp_message(
                        sender_identifier,
                        text=caption or None,
                        location=location,
                        receiving_phone_id=receiving_phone_id,
                        media_url=att.get("url"),
                        media_type=att.get("media_type") or "document",
                        media_filename=att.get("filename") or None,
                        media_mime=att.get("mime") or None,
                    )
                    if not ok:
                        return False, last_error
                return True, None
            ok, last_error = self.agent.send_whatsapp_message(
                sender_identifier,
                text=reply,
                location=location,
                receiving_phone_id=receiving_phone_id,
            )
            return bool(ok), last_error

        # Facebook: media first, then text — same as inbox composer.
        for att in media_items:
            ok, last_error = self.agent.send_facebook_message(
                sender_identifier,
                text=None,
                media_url=att.get("url"),
                media_type=att.get("media_type") or "file",
                media_mime=att.get("mime") or None,
                media_filename=att.get("filename") or None,
            )
            if not ok:
                return False, last_error
        if reply:
            ok, last_error = self.agent.send_facebook_message(sender_identifier, text=reply)
            if not ok:
                return False, last_error
        if not media_items and not reply:
            return False, "empty_payload"
        return True, None

    def _step_guard(self, step: dict, ctx: dict):
        path = str(step.get("path") or "event.payload.message_body").strip() or "event.payload.message_body"
        raw_val = _get_by_path(ctx, path)
        s = str(raw_val or "")
        ci = step.get("case_insensitive")
        ci = True if ci is None else bool(ci)
        hay = s.lower() if ci else s

        contains_any = step.get("contains_any")
        if contains_any is None:
            contains_any = step.get("contains")
        if contains_any is not None:
            if isinstance(contains_any, str):
                needles = [contains_any]
            elif isinstance(contains_any, list):
                needles = [str(x) for x in contains_any if str(x or "").strip()]
            else:
                needles = []
            ok = False
            for n in needles:
                nn = n.lower() if ci else n
                if nn and nn in hay:
                    ok = True
                    break
            if not ok:
                raise StopWorkflow("guard_blocked")

        regex = step.get("regex")
        if regex is not None and str(regex).strip():
            flags = re.IGNORECASE if ci else 0
            if not re.search(str(regex), s, flags=flags):
                raise StopWorkflow("guard_blocked")

    def _load_user_connections(self, company_id: str = ""):
        """FTS-native automation connections scoped per company (never Make.com)."""
        try:
            import chat_db
            import company_tenancy

            cid = automation_db.normalize_workflow_company_id(company_id) if company_id else ""
            if cid and not company_tenancy.is_default_company(cid):
                store_key = f"automation_app_connections__{cid}"
            else:
                store_key = "automation_app_connections"

            raw = chat_db.get_setting(store_key)
            data = json.loads(raw) if isinstance(raw, str) and raw.strip() else (raw or {})
            items = data.get("items") if isinstance(data, dict) else data
            if not isinstance(items, list):
                return []
            out = []
            for x in items:
                if not isinstance(x, dict):
                    continue
                item_cid = automation_db.normalize_workflow_company_id(
                    x.get("company_id") or x.get("companyId") or cid or ""
                )
                # Default store: skip explicitly foreign-tagged rows
                if store_key == "automation_app_connections":
                    if item_cid and not company_tenancy.is_default_company(item_cid):
                        continue
                elif cid and item_cid and item_cid != cid:
                    continue
                out.append(x)
            return out
        except Exception:
            return []

    def _find_connection(self, connection_id: str, connection_type: str = "", company_id: str = ""):
        cid = str(connection_id or "").strip()
        ctype = str(connection_type or "").strip().lower()
        items = self._load_user_connections(company_id)
        if cid:
            for it in items:
                if str(it.get("id") or "").strip() == cid:
                    return it
        if ctype:
            for it in items:
                if str(it.get("type") or "").strip().lower() == ctype:
                    return it
        # System defaults (Airtable only for default/FTS company)
        try:
            import company_tenancy

            is_fts = (not company_id) or company_tenancy.is_default_company(
                automation_db.normalize_workflow_company_id(company_id)
            )
        except Exception:
            is_fts = True
        if is_fts and (ctype == "airtable" or cid in ("system_airtable", "airtable_system")):
            return {"id": "system_airtable", "type": "airtable", "fields": {}, "source": "system"}
        if ctype in ("gmail", "outlook") or cid.startswith("legacy_gmail") or cid.startswith("gmail_"):
            return {"id": cid or "system_gmail", "type": ctype or "gmail", "fields": {"accountId": cid}, "source": "system"}

        # System / channel WhatsApp accounts (connection id often ends with phoneNumberId)
        if cid and ctype in ("", "whatsapp"):
            wa = self._resolve_system_whatsapp_connection(cid, company_id)
            if wa:
                return wa
        return None

    def _resolve_system_whatsapp_connection(self, connection_id: str, company_id: str = ""):
        """Map workflow connection_id → phoneNumberId / location from company channel settings."""
        cid = str(connection_id or "").strip()
        if not cid or cid in ("system_whatsapp",):
            return None

        def _match_and_return(phone_id, routing="", label="", access_token=""):
            phone_id = str(phone_id or "").strip()
            if not phone_id:
                return None
            return {
                "id": cid,
                "type": "whatsapp",
                "source": "system",
                "fields": {
                    "phoneNumberId": phone_id,
                    "routingLocation": str(routing or "").strip(),
                    "accessToken": str(access_token or "").strip(),
                    "label": str(label or phone_id).strip(),
                },
            }

        # 1) Agent legacy config phone_number_ids
        try:
            wa_cfg = (getattr(self.agent, "config", {}) or {}).get("whatsapp") or {}
            phone_number_ids = wa_cfg.get("phone_number_ids") if isinstance(wa_cfg, dict) else {}
            phone_id_locations = wa_cfg.get("phone_id_locations") if isinstance(wa_cfg, dict) else {}
            if isinstance(phone_number_ids, dict):
                for loc_key, raw_pid in phone_number_ids.items():
                    pid = str(raw_pid or "").strip()
                    if not pid:
                        continue
                    if cid.endswith(f"_{pid}") or cid == pid or cid.endswith(f"_{str(loc_key)}"):
                        routing = str(
                            (phone_id_locations.get(pid) if isinstance(phone_id_locations, dict) else "")
                            or loc_key
                            or ""
                        ).strip()
                        found = _match_and_return(pid, routing=routing, label=f"Meta {routing or loc_key}")
                        if found:
                            return found
        except Exception:
            pass

        # 2) Company channel settings (whatsappAccounts)
        try:
            import chat_db
            import company_tenancy

            company = (
                automation_db.normalize_workflow_company_id(company_id)
                if company_id
                else company_tenancy.DEFAULT_COMPANY_ID
            )
            key = "channel_settings"
            if not company_tenancy.is_default_company(company):
                key = f"channel_settings__{company}"
            raw = chat_db.get_setting(key)
            data = {}
            if isinstance(raw, str) and raw.strip():
                data = json.loads(raw)
            elif isinstance(raw, dict):
                data = raw
            wa_items = data.get("whatsappAccounts") if isinstance(data, dict) else None
            if not isinstance(wa_items, list):
                wa_items = []
            for ch in wa_items:
                if not isinstance(ch, dict):
                    continue
                wa_id = str(ch.get("id") or ch.get("phoneNumberId") or "").strip()
                phone_id = str(ch.get("phoneNumberId") or wa_id).strip()
                if not phone_id:
                    continue
                if (
                    cid.endswith(f"_{phone_id}")
                    or cid.endswith(f"_{wa_id}")
                    or cid in (phone_id, wa_id, f"{company}_{wa_id}", f"{company}_{phone_id}")
                ):
                    return _match_and_return(
                        phone_id,
                        routing=str(ch.get("routingLocation") or ch.get("location") or "").strip(),
                        label=str(ch.get("label") or ch.get("displayPhone") or phone_id).strip(),
                        access_token=str(ch.get("accessToken") or "").strip(),
                    )
        except Exception:
            pass

        # Fallback: connection id suffix looks like a Meta phone number id
        try:
            suffix = cid.split("_")[-1].strip()
            if suffix.isdigit() and len(suffix) >= 10:
                return _match_and_return(suffix)
        except Exception:
            pass
        return None

    def _connection_ctx(self, conn: dict):
        fields = conn.get("fields") if isinstance(conn.get("fields"), dict) else {}
        token = str(fields.get("token") or fields.get("accessToken") or "").strip()
        base_url = str(fields.get("baseUrl") or "").strip().rstrip("/")
        account_sid = str(fields.get("accountSid") or "").strip()
        from_number = str(fields.get("fromNumber") or "").strip()
        out = {
            "id": str(conn.get("id") or ""),
            "type": str(conn.get("type") or ""),
            "token": token,
            "baseUrl": base_url,
            "webhookUrl": str(fields.get("webhookUrl") or "").strip(),
            "bridgeSecret": str(fields.get("bridgeSecret") or "").strip(),
            "accountSid": account_sid,
            "fromNumber": from_number,
            "accountId": str(fields.get("accountId") or conn.get("id") or ""),
        }
        if token and str(conn.get("type") or "").lower() == "telegram":
            out["telegram_send_url"] = f"https://api.telegram.org/bot{token}/sendMessage"
        if account_sid:
            out["twilio_messages_url"] = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        return out

    def _apply_connection_auth(self, step: dict, headers: dict, ctx: dict):
        conn_id = str(step.get("connection_id") or "").strip()
        conn_type = str(step.get("connection_type") or "").strip().lower()
        if not conn_id and not conn_type:
            return headers
        company_id = str((ctx or {}).get("company_id") or "").strip()
        conn = self._find_connection(conn_id, conn_type, company_id=company_id)
        if not conn:
            return headers
        cctx = self._connection_ctx(conn)
        ctx["connection"] = cctx
        token = cctx.get("token") or ""
        ctype = str(cctx.get("type") or conn_type).lower()
        h = dict(headers or {})
        if ctype in ("airtable", "slack", "stripe", "google_sheets", "notion", "deepseek", "gemini", "openai") and token:
            h.setdefault("Authorization", f"Bearer {token}")
        elif ctype == "baserow" and token:
            h.setdefault("Authorization", f"Token {token}")
        elif ctype == "supabase" and token:
            h.setdefault("apikey", token)
            h.setdefault("Authorization", f"Bearer {token}")
        elif ctype == "http" and token:
            fields = conn.get("fields") if isinstance(conn.get("fields"), dict) else {}
            header_name = str(fields.get("headerName") or "Authorization").strip() or "Authorization"
            prefix = str(fields.get("headerPrefix") if fields.get("headerPrefix") is not None else "Bearer ")
            h.setdefault(header_name, f"{prefix}{token}")
        elif ctype == "twilio":
            # Basic auth via requests auth= handled in http step
            ctx["_http_basic"] = (cctx.get("accountSid") or "", token)
        if ctype == "notion":
            h.setdefault("Notion-Version", "2022-06-28")
        return h

    def _step_set_variable(self, step: dict, ctx: dict):
        key = str(step.get("key") or "value").strip() or "value"
        val = step.get("value")
        if isinstance(val, str):
            val = _render_template(val, ctx)
        ctx.setdefault("vars", {})[key] = val

    def _step_text_parser(self, step: dict, ctx: dict):
        text = _render_template(step.get("text") or "", ctx)
        pattern = str(step.get("pattern") or "")
        output_key = str(step.get("output_key") or "parsed").strip() or "parsed"
        group = int(step.get("group") or 1)
        if not pattern:
            return
        m = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            ctx.setdefault("vars", {})[output_key] = ""
            return
        try:
            ctx.setdefault("vars", {})[output_key] = m.group(group)
        except IndexError:
            ctx.setdefault("vars", {})[output_key] = m.group(0)

    def _step_json_parse(self, step: dict, ctx: dict):
        text = _render_template(step.get("text") or "", ctx)
        output_key = str(step.get("output_key") or "json").strip() or "json"
        try:
            ctx.setdefault("vars", {})[output_key] = json.loads(text)
        except Exception:
            ctx.setdefault("vars", {})[output_key] = None

    def _step_sleep(self, step: dict, ctx: dict):
        try:
            seconds = float(step.get("seconds") or 1)
        except Exception:
            seconds = 1.0
        seconds = max(0.0, min(seconds, 30.0))
        if seconds > 0:
            time.sleep(seconds)

    def _step_ai(self, step: dict, ctx: dict):
        prompt = _render_template(step.get("prompt") or "", ctx)
        system_role = str(step.get("system_role") or "analyzer").strip() or "analyzer"
        output_key = str(step.get("output_key") or "ai").strip() or "ai"
        if not prompt:
            return
        wf = ctx.get("workflow") if isinstance(ctx.get("workflow"), dict) else {}
        wf_label = str(wf.get("name") or wf.get("id") or "unknown").strip() or "unknown"
        usage_source = f"automation:{wf_label}"
        # preferred_provider is advisory; query_ai uses system routing.
        # Connection id is stored for future provider-specific overrides.
        _ = str(step.get("preferred_provider") or step.get("connection_id") or "")
        res = self.agent.query_ai(prompt, system_role=system_role, usage_source=usage_source)
        ctx["vars"][output_key] = res

    def _step_send_email(self, step: dict, ctx: dict):
        to_email = _render_template(step.get("to") or "", ctx).strip()
        if not to_email:
            to_email = str(_get_by_path(ctx, "event.payload.sender_identifier") or "").strip()
        if not to_email or "@" not in to_email:
            raise Exception("send_email_missing_to")

        subject = _render_template(step.get("subject") or "", ctx).strip() or "FTS Travels"
        body_html = _render_template(step.get("html") or "", ctx).strip()
        if not body_html:
            return
        thread_id = str(_get_by_path(ctx, "event.payload.thread_id") or "").strip() or None
        mailbox = str(step.get("mailbox") or step.get("connection_id") or "").strip() or None
        if mailbox in ("system_gmail", "system_outlook", ""):
            mailbox = None
        try:
            self.agent.send_email(to_email, subject, body_html, thread_id=thread_id, mailbox=mailbox)
        except TypeError:
            self.agent.send_email(to_email, subject, body_html, thread_id=thread_id)

    def _step_airtable_update(self, step: dict, ctx: dict):
        record_id = _render_template(step.get("record_id") or "", ctx).strip()
        if not record_id:
            record_id = str(_get_by_path(ctx, "chat.airtable_record_id") or "").strip()
        if not record_id:
            raise Exception("airtable_update_missing_record_id")

        fields = step.get("fields") or {}
        if not isinstance(fields, dict):
            raise Exception("airtable_update_invalid_fields")

        rendered = {}
        for k, v in fields.items():
            key = str(k or "").strip()
            if not key:
                continue
            if isinstance(v, str):
                rendered[key] = _render_template(v, ctx)
            else:
                rendered[key] = v

        if not rendered:
            return
        if not getattr(self.agent, "table", None):
            raise Exception("airtable_not_configured")
        self.agent.table.update(record_id, rendered)

    def _step_send_internal_notification(self, step: dict, ctx: dict):
        """Send via Internal Notifications Evolution channel (staff alerts)."""
        to_phone = _render_template(step.get("to") or step.get("phone") or "", ctx).strip()
        to_phone = to_phone.replace("+", "").replace(" ", "")
        if not to_phone:
            raise Exception("send_internal_notification_missing_to")
        text = _render_template(step.get("text") or "", ctx).strip()
        if not text:
            return
        if not self.agent or not hasattr(self.agent, "send_internal_notifications_whatsapp_text"):
            raise Exception("send_internal_notification_unavailable")
        ok = bool(self.agent.send_internal_notifications_whatsapp_text(to_phone, text))
        if not ok:
            raise Exception("send_internal_notification_failed")
        ctx.setdefault("vars", {})["_workflow_sent"] = True

    def _step_send_whatsapp(self, step: dict, ctx: dict):
        to_phone = _render_template(step.get("to") or "", ctx).strip()
        if not to_phone:
            to_phone = str(_get_by_path(ctx, "event.payload.sender_identifier") or "").strip()
        to_phone = to_phone.replace("+", "").replace(" ", "").replace("-", "")
        if not to_phone:
            raise Exception("send_whatsapp_missing_to")

        mode = str(step.get("message_mode") or "").strip().lower()
        template_name = _render_template(step.get("template_name") or "", ctx).strip()
        if not mode:
            mode = "template" if template_name else "text"

        text = _render_template(step.get("text") or "", ctx).strip()
        template_language = _render_template(step.get("template_language") or "en", ctx).strip() or "en"

        template_variables = step.get("template_variables")
        if template_variables is None and step.get("template_variables_json"):
            raw_vars = step.get("template_variables_json")
            if isinstance(raw_vars, str) and raw_vars.strip():
                try:
                    template_variables = json.loads(_render_template(raw_vars, ctx))
                except Exception:
                    template_variables = None
        if isinstance(template_variables, dict):
            rendered_vars = {}
            for k, v in template_variables.items():
                rendered_vars[str(k)] = _render_template(v, ctx) if isinstance(v, str) else v
            template_variables = rendered_vars

        if mode == "template":
            if not template_name:
                raise Exception("send_whatsapp_missing_template")
        elif not text:
            raise Exception("send_whatsapp_missing_text")

        location = str(
            _render_template(step.get("location") or "", ctx).strip()
            or _get_by_path(ctx, "chat.location")
            or _get_by_path(ctx, "event.payload.location")
            or "Unknown"
        ).strip() or "Unknown"
        receiving_phone_id = str(
            _render_template(step.get("receiving_phone_id") or "", ctx).strip()
            or _get_by_path(ctx, "chat.receiving_phone_id")
            or _get_by_path(ctx, "event.payload.receiving_phone_id")
            or ""
        ).strip() or None

        conn_id = str(step.get("connection_id") or "").strip()
        if conn_id and conn_id not in ("system_whatsapp",):
            conn = self._find_connection(
                conn_id,
                "whatsapp",
                company_id=str((ctx or {}).get("company_id") or ""),
            )
            if conn:
                fields = conn.get("fields") if isinstance(conn.get("fields"), dict) else {}
                phone_id = str(fields.get("phoneNumberId") or "").strip()
                if phone_id and not receiving_phone_id:
                    receiving_phone_id = phone_id
                elif phone_id and receiving_phone_id and phone_id != receiving_phone_id:
                    # Explicit Sender ID wins (Make behavior)
                    pass
                loc_hint = str(fields.get("routingLocation") or fields.get("location") or "").strip()
                if loc_hint and (not location or location == "Unknown"):
                    location = loc_hint

        if mode == "template" and not receiving_phone_id and (not location or location == "Unknown"):
            raise Exception(
                "send_whatsapp_missing_sender: select Sender ID (Meta phone number) like Make"
            )

        ok, err = self.agent.send_whatsapp_message(
            to_phone,
            text=None if mode == "template" else text,
            location=location,
            template_name=template_name if mode == "template" else None,
            template_language=template_language,
            template_variables=template_variables if mode == "template" else None,
            receiving_phone_id=receiving_phone_id,
        )
        if not ok:
            detail = ""
            try:
                if isinstance(err, dict):
                    detail = str(
                        ((err.get("json") or {}).get("error") or {}).get("message")
                        or err.get("body")
                        or err.get("code")
                        or err
                    )[:400]
                else:
                    detail = str(err or "")[:400]
            except Exception:
                detail = "send_failed"
            raise Exception(f"send_whatsapp_failed:{detail or 'unknown'}")

        # Stash rendered summary for operation inspector
        ctx.setdefault("vars", {})["_last_whatsapp_send"] = {
            "to": to_phone,
            "mode": mode,
            "template_name": template_name if mode == "template" else None,
            "template_language": template_language if mode == "template" else None,
            "text": text if mode == "text" else None,
            "location": location,
            "receiving_phone_id": receiving_phone_id,
        }

        chat_id = str(_get_by_path(ctx, "chat.chat_id") or _get_by_path(ctx, "event.payload.chat_id") or "").strip()
        if ok and chat_id:
            try:
                import chat_db

                log_text = (
                    f"[Sent WhatsApp] Template: {template_name}"
                    if mode == "template"
                    else text
                )
                chat_db.add_message(chat_id=chat_id, sender_type="agent", text=log_text, status="sent", source="WhatsApp")
            except Exception:
                pass

    def _mark_sent_from_script_result(self, ctx: dict, result):
        """Propagate workflow script `sent: True` so sync callers can skip AI drafts."""
        try:
            data = result
            if isinstance(result, dict) and isinstance(result.get("data"), dict):
                data = result.get("data")
            if isinstance(data, dict) and data.get("sent"):
                ctx.setdefault("vars", {})["_workflow_sent"] = True
                chat_id = str(
                    data.get("chat_id")
                    or _get_by_path(ctx, "event.payload.chat_id")
                    or ""
                ).strip()
                if chat_id and self.agent and hasattr(self.agent, "mark_workflow_live_reply"):
                    try:
                        self.agent.mark_workflow_live_reply(chat_id, reason="automation_script_sent")
                    except Exception:
                        pass
        except Exception:
            pass

    def _try_run_local_automation_script(self, url: str, body, ctx: dict, output_key: str):
        """
        Avoid HTTP self-calls to /api/automation/run_script during sync handling.
        Those deadlock or race with the AI draft path on single-worker servers.
        """
        u = str(url or "").strip().lower()
        if "/api/automation/run_script" not in u:
            return False
        if not isinstance(body, dict):
            return False
        script_name = str(body.get("script_name") or "").strip()
        if not script_name:
            return False
        if not self.agent or not hasattr(self.agent, "run_automation_script"):
            return False

        rendered_body = {}
        for k, v in body.items():
            if isinstance(v, str):
                rendered_body[k] = _render_template(v, ctx)
            else:
                rendered_body[k] = v

        result = self.agent.run_automation_script(script_name, rendered_body)
        if not isinstance(result, dict):
            raise Exception("run_script_invalid_result")
        if str(result.get("status") or "").lower() == "error":
            raise Exception(f"run_script_failed:{result.get('message') or 'unknown'}")

        if output_key:
            ctx.setdefault("vars", {})[output_key] = result
        self._mark_sent_from_script_result(ctx, result)
        return True

    def _try_run_local_fts_workflow(self, url: str, body, ctx: dict, output_key: str):
        """
        Run local FTS bulk workflows in-process instead of HTTP self-call.
        Offer Send can take >60s (Meta template fetch + WhatsApp send per record),
        and the HTTP client used to hard-cap at 60s.
        """
        u = str(url or "").strip().lower()
        local = ("127.0.0.1" in u) or ("localhost" in u)
        if not local or not isinstance(body, dict) or not self.agent:
            return False

        runner = None
        payload_extra = {}
        if "/api/offer_send_fts/run" in u:
            from offer_send_fts import run as runner
        elif "/api/offer_bonus_fts/run" in u:
            from offer_bonus_fts import run as runner
        elif "/api/cancelled_recovery_bonus_fts/run" in u:
            from cancelled_recovery_fts import run as runner
            payload_extra = {"mode": "bonus"}
        elif "/api/cancelled_recovery_fts/run" in u:
            from cancelled_recovery_fts import run as runner
        else:
            return False

        rendered_body = {}
        for k, v in body.items():
            if isinstance(v, str):
                rendered_body[k] = _render_template(v, ctx)
            else:
                rendered_body[k] = v
        if payload_extra:
            rendered_body.update(payload_extra)

        result = runner(self.agent, rendered_body)
        if not isinstance(result, dict):
            raise Exception("fts_workflow_invalid_result")
        if str(result.get("status") or "").lower() == "error":
            raise Exception(f"fts_workflow_failed:{result.get('message') or 'unknown'}")

        if output_key:
            ctx.setdefault("vars", {})[output_key] = result
        self._mark_sent_from_script_result(ctx, result)
        return True

    def _step_http_request(self, step: dict, ctx: dict):
        # Inject connection secrets into ctx before URL/body template render.
        headers = step.get("headers") or {}
        if not isinstance(headers, dict):
            headers = {}
        ctx.pop("_http_basic", None)
        seed_headers = {str(k): (v if not isinstance(v, str) else v) for k, v in headers.items() if k}
        rendered_headers = self._apply_connection_auth(step, seed_headers, ctx)

        method = str(step.get("method") or "POST").strip().upper()
        url = _render_template(step.get("url") or "", ctx).strip()
        if not url:
            raise Exception("http_request_missing_url")

        final_headers = {}
        for k, v in rendered_headers.items():
            if isinstance(v, str):
                final_headers[str(k)] = _render_template(v, ctx)
            else:
                final_headers[str(k)] = str(v)
        rendered_headers = final_headers

        # Make-like query parameters (JSON object → URL query string).
        query = step.get("query")
        if isinstance(query, dict) and query:
            from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

            parts = urlsplit(url)
            merged = dict(parse_qsl(parts.query, keep_blank_values=True))
            for qk, qv in query.items():
                if qv is None:
                    continue
                if isinstance(qv, str):
                    merged[str(qk)] = _render_template(qv, ctx)
                else:
                    merged[str(qk)] = str(qv)
            url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(merged, doseq=True), parts.fragment))

        body = step.get("body")
        output_key = str(step.get("output_key") or "result").strip()
        parse_response = step.get("parse_response")
        if parse_response is None:
            parse_response = True
        fail_on_http_error = step.get("fail_on_http_error")
        if fail_on_http_error is None:
            fail_on_http_error = True
        allow_redirects = step.get("allow_redirects")
        if allow_redirects is None:
            allow_redirects = True

        # Prefer in-process script execution for local automation run_script URLs.
        # Avoids HTTP self-call deadlocks/races that let AI insert a late PROPOSED_DRAFT.
        if method == "POST" and isinstance(body, dict):
            if self._try_run_local_automation_script(url, body, ctx, output_key):
                return
            if self._try_run_local_fts_workflow(url, body, ctx, output_key):
                return

        timeout_s = step.get("timeout_seconds")
        try:
            timeout_s = float(timeout_s) if timeout_s is not None else 15.0
        except Exception:
            timeout_s = 15.0
        timeout_s = max(1.0, min(timeout_s, 300.0))

        auth = None
        basic = ctx.get("_http_basic")
        if isinstance(basic, (list, tuple)) and len(basic) == 2:
            auth = (str(basic[0] or ""), str(basic[1] or ""))

        def _send(**kwargs):
            res = requests.request(
                method,
                url,
                headers=rendered_headers,
                timeout=timeout_s,
                auth=auth,
                allow_redirects=bool(allow_redirects),
                **kwargs,
            )
            sc = int(getattr(res, "status_code", 0) or 0)
            if fail_on_http_error and sc >= 400:
                try:
                    body_text = (res.text or "")[:1500]
                except Exception:
                    body_text = ""
                raise Exception(f"http_request_failed_{sc}:{body_text}")
            try:
                if output_key:
                    ct = str(res.headers.get("content-type") or "").lower()
                    parsed = None
                    if parse_response and "application/json" in ct:
                        try:
                            parsed = res.json()
                            ctx["vars"][output_key] = parsed
                        except Exception:
                            ctx["vars"][output_key] = (res.text or "")
                    else:
                        ctx["vars"][output_key] = (res.text or "")
                    if parsed is not None:
                        self._mark_sent_from_script_result(ctx, parsed)
            except Exception:
                pass
            return res

        if body is None:
            _send()
            return

        if isinstance(body, str):
            b = _render_template(body, ctx)
            _send(data=b.encode("utf-8"))
            return

        if isinstance(body, dict):
            rendered_body = {}
            for k, v in body.items():
                if isinstance(v, str):
                    rendered_body[k] = _render_template(v, ctx)
                else:
                    rendered_body[k] = v
            ct = str(rendered_headers.get("content-type") or rendered_headers.get("Content-Type") or "").lower()
            if "application/x-www-form-urlencoded" in ct:
                _send(data=rendered_body)
            else:
                _send(json=rendered_body)
            return

        _send(data=str(body))
