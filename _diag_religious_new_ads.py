# -*- coding: utf-8 -*-
"""Diagnostics for religious_new_ads_followup workflow."""
from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timedelta

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

from fts_paths import get_data_path

WF_ID = "religious_new_ads_followup_v1"
STATE_PATH = get_data_path("religious_new_ads_followup_state.json")
CFG_PATH = get_data_path("religious_new_ads_followup_config.json")
CHAT_DB = get_data_path("chat_history.db")


def _parse_dt(value):
    if not value:
        return None
    try:
        s = str(value)
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        d = datetime.fromisoformat(s)
    except Exception:
        try:
            d = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None
    if d.tzinfo is not None:
        d = d.replace(tzinfo=None)
    return d


def section(title):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def main():
    print("CWD:", os.getcwd())
    print("CHAT_DB:", CHAT_DB, "exists=", os.path.exists(CHAT_DB))
    print("STATE:", STATE_PATH, "exists=", os.path.exists(STATE_PATH))
    print("CFG:", CFG_PATH, "exists=", os.path.exists(CFG_PATH))

    # ------------------------------------------------------------------
    # 1) Workflow row in automation_db
    # ------------------------------------------------------------------
    section("1) WORKFLOW ROW")
    try:
        import automation_db

        automation_db.init_db()
        wf = automation_db.get_workflow(WF_ID)
        if not wf:
            print("NOT FOUND:", WF_ID)
            wfs = automation_db.list_workflows()
            print("total workflows:", len(wfs))
            for w in wfs:
                wid = str(w.get("id") or "")
                if "religious" in wid.lower() or "new_ads" in wid.lower() or "followup" in wid.lower():
                    print(" candidate:", wid, "enabled=", w.get("enabled"))
        else:
            print("id:", wf.get("id"))
            print("name:", (wf.get("name") or "")[:120])
            print("enabled:", wf.get("enabled"))
            print("trigger_type:", wf.get("trigger_type"))
            print("trigger_config:", wf.get("trigger_config_json") or wf.get("trigger_config"))
            print("last_run_at:", wf.get("last_run_at"))
            print("last_error:", wf.get("last_error"))
            print("updated_at:", wf.get("updated_at"))
            print("created_at:", wf.get("created_at"))
            steps = wf.get("steps_json") or "[]"
            print("steps_json:", steps[:500])

            runs = automation_db.list_runs(WF_ID, limit=15)
            print("recent_runs_count:", len(runs))
            for r in runs[:10]:
                print(
                    " run:",
                    r.get("id"),
                    "status=",
                    r.get("status"),
                    "started=",
                    r.get("started_at"),
                    "finished=",
                    r.get("finished_at"),
                    "error=",
                    (r.get("error") or "")[:200],
                )
                payload = r.get("event_payload_json") or ""
                if payload:
                    print("  payload_snip:", str(payload)[:300])
    except Exception:
        print("automation_db ERROR:")
        traceback.print_exc()

    # ------------------------------------------------------------------
    # 2) State file stats
    # ------------------------------------------------------------------
    section("2) STATE FILE")
    try:
        now = datetime.utcnow() + timedelta(hours=3)  # Cairo approx
        try:
            import chat_db

            now = datetime.fromisoformat(chat_db.get_cairo_time()).replace(tzinfo=None)
        except Exception:
            pass
        print("now_cairo_approx:", now.isoformat())

        if not os.path.exists(STATE_PATH):
            print("STATE FILE MISSING")
        else:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            chats = data.get("chats") if isinstance(data, dict) else {}
            if not isinstance(chats, dict):
                chats = {}
            meta = {k: v for k, v in (data.items() if isinstance(data, dict) else []) if k != "chats"}
            print("meta:", json.dumps(meta, ensure_ascii=True, default=str)[:800])
            print("total_chats:", len(chats))

            stage_ge1 = 0
            handled = 0
            seq_done = 0
            opted = 0
            stage0_unhandled = []
            stage_hist = {0: 0, 1: 0, 2: 0, "other": 0}

            for cid, e in chats.items():
                if not isinstance(e, dict):
                    continue
                hs = int(e.get("highest_stage_sent") or 0)
                if hs >= 1:
                    stage_ge1 += 1
                if hs in stage_hist:
                    stage_hist[hs] += 1
                else:
                    stage_hist["other"] += 1
                if e.get("handled"):
                    handled += 1
                if e.get("sequence_done"):
                    seq_done += 1
                if e.get("opted_out"):
                    opted += 1
                if hs == 0 and not e.get("handled") and not e.get("sequence_done") and not e.get("opted_out"):
                    anchor = _parse_dt(e.get("last_customer_reply"))
                    age_h = None
                    if anchor:
                        age_h = (now - anchor).total_seconds() / 3600.0
                    stage0_unhandled.append(
                        {
                            "chat_id": cid,
                            "last_customer_reply": e.get("last_customer_reply"),
                            "age_hours": round(age_h, 3) if age_h is not None else None,
                            "handled_reason": e.get("handled_reason"),
                            "updated_at": e.get("updated_at"),
                            "last_customer_text": str(e.get("last_customer_text") or "")[:80],
                        }
                    )

            print("highest_stage_sent>=1:", stage_ge1)
            print("handled=true:", handled)
            print("sequence_done:", seq_done)
            print("opted_out:", opted)
            print("stage_histogram:", stage_hist)
            print("stuck_stage0_unhandled:", len(stage0_unhandled))

            # age buckets for stuck
            buckets = {"lt3": 0, "3to23": 0, "23to2375": 0, "2375to24": 0, "ge24": 0, "unknown": 0}
            for s in stage0_unhandled:
                a = s.get("age_hours")
                if a is None:
                    buckets["unknown"] += 1
                elif a < 3:
                    buckets["lt3"] += 1
                elif a < 23:
                    buckets["3to23"] += 1
                elif a < 23.75:
                    buckets["23to2375"] += 1
                elif a < 24:
                    buckets["2375to24"] += 1
                else:
                    buckets["ge24"] += 1
            print("stuck_age_buckets:", buckets)

            # sample 3 stuck: prefer those in sendable window (3-23) then oldest
            sendable = [s for s in stage0_unhandled if s.get("age_hours") is not None and 3 <= s["age_hours"] < 23]
            sendable.sort(key=lambda x: -(x.get("age_hours") or 0))
            sample_src = sendable if sendable else sorted(
                stage0_unhandled, key=lambda x: -(x.get("age_hours") or -1)
            )
            print("sample_stuck (up to 3):")
            for s in sample_src[:3]:
                print(" ", json.dumps(s, ensure_ascii=True, default=str))
    except Exception:
        print("STATE ERROR:")
        traceback.print_exc()

    # ------------------------------------------------------------------
    # 3) Dry-run of workflow
    # ------------------------------------------------------------------
    section("3) DRY_RUN")
    try:
        from workflows import religious_new_ads_followup as mod

        class DummyAgent:
            def send_whatsapp_message(self, *a, **k):
                return True, "dry"

            def send_facebook_message(self, *a, **k):
                return True, "dry"

        result = mod.run(DummyAgent(), {"dry_run": True})
        print(json.dumps(result, ensure_ascii=True, default=str, indent=2))
    except Exception:
        print("DRY_RUN ERROR:")
        traceback.print_exc()

    # ------------------------------------------------------------------
    # 4) Logic bug confirmation: first-pass continue
    # ------------------------------------------------------------------
    section("4) LOGIC CHECK (first-pass / WINDOW)")
    try:
        import inspect
        from workflows import religious_new_ads_followup as mod

        src = inspect.getsource(mod.run)
        has_init_continue = "if entry is None:" in src and "continue" in src
        print("TARGET_AD_IDS:", mod.TARGET_AD_IDS)
        print("STAGE1_HOURS:", mod.STAGE1_HOURS)
        print("STAGE2_HOURS:", mod.STAGE2_HOURS)
        print("STAGE2_SAFE_MAX:", mod.STAGE2_SAFE_MAX)
        print("WINDOW_HOURS:", mod.WINDOW_HOURS)
        print("MAX_SENDS_PER_RUN:", mod.MAX_SENDS_PER_RUN)

        # Count DB-eligible vs state
        import sqlite3

        conn = sqlite3.connect(CHAT_DB, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        placeholders = ",".join("?" * len(mod.TARGET_AD_IDS))
        cur.execute(
            f"""
            SELECT COUNT(*) AS n FROM conversations
            WHERE facebook_ad_id IN ({placeholders})
              AND location = ?
              AND (is_deleted IS NULL OR is_deleted = 0)
              AND last_message_time IS NOT NULL
            """,
            (*mod.TARGET_AD_IDS, mod.TARGET_LOCATION),
        )
        print("db_matching_conversations:", cur.fetchone()["n"])

        # within last 24h by last_message_time
        now2 = mod._now()
        cur.execute(
            f"""
            SELECT chat_id, last_message_time, needs_help, is_closed, auto_reply_hold_until
            FROM conversations
            WHERE facebook_ad_id IN ({placeholders})
              AND location = ?
              AND (is_deleted IS NULL OR is_deleted = 0)
              AND last_message_time IS NOT NULL
            ORDER BY last_message_time DESC
            LIMIT 5000
            """,
            (*mod.TARGET_AD_IDS, mod.TARGET_LOCATION),
        )
        rows = cur.fetchall()
        within24 = 0
        blocked_help = 0
        blocked_closed = 0
        blocked_hold = 0
        for r in rows:
            lmt = mod._parse_dt(r["last_message_time"])
            if lmt and (now2 - lmt).total_seconds() / 3600.0 <= mod.WINDOW_HOURS:
                within24 += 1
                try:
                    if int(r["needs_help"] or 0) == 1:
                        blocked_help += 1
                except Exception:
                    pass
                try:
                    if int(r["is_closed"] or 0) == 1:
                        blocked_closed += 1
                except Exception:
                    pass
                if mod._hold_active(r["auto_reply_hold_until"], now2):
                    blocked_hold += 1
        print("db_within_24h_last_message_time:", within24)
        print("of_those needs_help:", blocked_help, "is_closed:", blocked_closed, "hold:", blocked_hold)

        # Simulate: for stage0 unhandled in state, would _target_stage fire?
        if os.path.exists(STATE_PATH):
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                chats = (json.load(f) or {}).get("chats") or {}
            would_send1 = 0
            would_send2 = 0
            wait = 0
            past_window = 0
            for cid, e in chats.items():
                if not isinstance(e, dict):
                    continue
                if e.get("handled") or e.get("sequence_done") or e.get("opted_out"):
                    continue
                hs = int(e.get("highest_stage_sent") or 0)
                anchor = mod._parse_dt(e.get("last_customer_reply"))
                if not anchor:
                    continue
                elapsed = (now2 - anchor).total_seconds() / 3600.0
                if elapsed >= mod.WINDOW_HOURS:
                    past_window += 1
                    continue
                t = mod._target_stage(elapsed, hs)
                if t == 1:
                    would_send1 += 1
                elif t == 2:
                    would_send2 += 1
                else:
                    wait += 1
            print("state_eligible_would_send_stage1:", would_send1)
            print("state_eligible_would_send_stage2:", would_send2)
            print("state_waiting_timing:", wait)
            print("state_past_window_unhandled:", past_window)

        print(
            "BUG_NOTE: on first encounter entry is None -> init + continue ALWAYS "
            "(no send same pass). Stage messages only on a LATER run once entry exists."
        )
        conn.close()
    except Exception:
        print("LOGIC CHECK ERROR:")
        traceback.print_exc()

    # ------------------------------------------------------------------
    # 5) Search log files
    # ------------------------------------------------------------------
    section("5) LOG FILES")
    log_hits = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "frontend_dashboard", "make.com", "__pycache__")]
        for fn in files:
            low = fn.lower()
            if not (low.endswith(".log") or low.endswith(".ndjson") or "automation" in low):
                continue
            path = os.path.join(root, fn)
            try:
                if os.path.getsize(path) > 20_000_000:
                    continue
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
                if "religious_new_ads" in txt or "NewAds" in txt or "ReligiousNewAds" in txt:
                    log_hits.append(path)
            except Exception:
                pass
    print("log_files_with_mentions:", log_hits[:20] if log_hits else "NONE")

    # Also check automation_runs payloads more carefully already done above
    print("\nDONE")


if __name__ == "__main__":
    main()
