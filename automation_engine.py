import json
import threading
import time
import re
from datetime import datetime

import requests

import automation_db


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


class StopWorkflow(Exception):
    pass


class AutomationEngine:
    def __init__(self, agent):
        self.agent = agent
        self._schedule_state = {}
        self._lock = threading.Lock()
        self._tick_last = 0.0

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

                self._schedule_state[wid] = {"last_ts": time.time()}
                threading.Thread(
                    target=self._run_workflow_by_id,
                    args=(wid,),
                    kwargs={"event_type": "schedule", "event_payload": {"trigger": trigger_cfg}},
                    daemon=True,
                ).start()
            except Exception:
                continue

    def _handle_event(self, event_type: str, payload: dict):
        any_sent = False
        try:
            workflows = automation_db.list_workflows()
        except Exception:
            workflows = []

        for wf in workflows:
            try:
                if int(wf.get("enabled") or 0) != 1:
                    continue
                if str(wf.get("trigger_type") or "").strip().lower() != str(event_type or "").strip().lower():
                    continue

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

        ctx = {
            "now": _utc_now(),
            "event": {"type": event_type, "payload": event_payload or {}},
            "vars": {},
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
        try:
            for step in steps:
                if not isinstance(step, dict):
                    continue
                stype = str(step.get("type") or "").strip().lower()
                if not stype:
                    continue
                if stype == "guard":
                    self._step_guard(step, ctx)
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
                else:
                    continue
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
                    automation_db.finish_run(run_id, "success" if not err else "error", error=err, payload=final_payload)
                except Exception:
                    pass
        sent = bool((ctx.get("vars") or {}).get("_workflow_sent"))
        return {"ok": err is None, "error": err, "sent": sent}

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

    def _step_ai(self, step: dict, ctx: dict):
        prompt = _render_template(step.get("prompt") or "", ctx)
        system_role = str(step.get("system_role") or "analyzer").strip() or "analyzer"
        output_key = str(step.get("output_key") or "ai").strip() or "ai"
        if not prompt:
            return
        res = self.agent.query_ai(prompt, system_role=system_role)
        ctx["vars"][output_key] = res

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

    def _step_send_whatsapp(self, step: dict, ctx: dict):
        to_phone = _render_template(step.get("to") or "", ctx).strip()
        if not to_phone:
            to_phone = str(_get_by_path(ctx, "event.payload.sender_identifier") or "").strip()
        to_phone = to_phone.replace("+", "").replace(" ", "")
        if not to_phone:
            raise Exception("send_whatsapp_missing_to")

        text = _render_template(step.get("text") or "", ctx).strip()
        if not text:
            return

        location = str(_get_by_path(ctx, "chat.location") or _get_by_path(ctx, "event.payload.location") or "Unknown").strip() or "Unknown"
        receiving_phone_id = str(_get_by_path(ctx, "chat.receiving_phone_id") or _get_by_path(ctx, "event.payload.receiving_phone_id") or "").strip() or None
        ok, _ = self.agent.send_whatsapp_message(to_phone, text=text, location=location, receiving_phone_id=receiving_phone_id)

        chat_id = str(_get_by_path(ctx, "chat.chat_id") or _get_by_path(ctx, "event.payload.chat_id") or "").strip()
        if ok and chat_id:
            try:
                import chat_db

                chat_db.add_message(chat_id=chat_id, sender_type="agent", text=text, status="sent", source="WhatsApp")
            except Exception:
                pass

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
        self.agent.send_email(to_email, subject, body_html, thread_id=thread_id)

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

    def _step_http_request(self, step: dict, ctx: dict):
        method = str(step.get("method") or "POST").strip().upper()
        url = _render_template(step.get("url") or "", ctx).strip()
        if not url:
            raise Exception("http_request_missing_url")

        headers = step.get("headers") or {}
        if not isinstance(headers, dict):
            headers = {}
        rendered_headers = {}
        for k, v in headers.items():
            if not k:
                continue
            if isinstance(v, str):
                rendered_headers[str(k)] = _render_template(v, ctx)
            else:
                rendered_headers[str(k)] = str(v)

        body = step.get("body")
        output_key = str(step.get("output_key") or "result").strip()

        # Prefer in-process script execution for local automation run_script URLs.
        # Avoids HTTP self-call deadlocks/races that let AI insert a late PROPOSED_DRAFT.
        if method == "POST" and isinstance(body, dict):
            if self._try_run_local_automation_script(url, body, ctx, output_key):
                return

        timeout_s = step.get("timeout_seconds")
        try:
            timeout_s = float(timeout_s) if timeout_s is not None else 15.0
        except Exception:
            timeout_s = 15.0
        timeout_s = max(1.0, min(timeout_s, 60.0))

        def _send(**kwargs):
            res = requests.request(method, url, headers=rendered_headers, timeout=timeout_s, **kwargs)
            sc = int(getattr(res, "status_code", 0) or 0)
            if sc >= 400:
                try:
                    body_text = (res.text or "")[:1500]
                except Exception:
                    body_text = ""
                raise Exception(f"http_request_failed_{sc}:{body_text}")
            try:
                if output_key:
                    ct = str(res.headers.get("content-type") or "").lower()
                    parsed = None
                    if "application/json" in ct:
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
            _send(json=rendered_body)
            return

        _send(data=str(body))
