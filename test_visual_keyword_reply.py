# -*- coding: utf-8 -*-
"""Tests for visual Workflow Builder keyword_reply engine step (no PI / no Python files)."""
import sys
import io
import os
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from automation_engine import (
    AutomationEngine,
    StopWorkflow,
    keyword_matches,
    normalize_keyword_text,
    is_non_text_media_message,
)


class MockAgent:
    def __init__(self):
        self.sent = []
        self.live = []
        self.cancelled = []

    def send_whatsapp_message(self, recipient, text=None, location="Unknown", receiving_phone_id=None, **kw):
        self.sent.append(("whatsapp", recipient, text, location, receiving_phone_id))
        return True, None

    def send_facebook_message(self, recipient, text=None, **kw):
        self.sent.append(("facebook", recipient, text))
        return True, None

    def mark_workflow_live_reply(self, chat_id, reason="workflow"):
        self.live.append((chat_id, reason))

    def cancel_whatsapp_ai_processing(self, **kw):
        self.cancelled.append(kw)
        return True


results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


KW = "🕋 الراحة والقرب من الحرم"
REPLY = "اختيار موفق 👍 الأنسب لحضرتك غالبًا برنامج التحسين."


def step_for(mode="phrase", keywords=None, reply=REPLY):
    return {
        "type": "keyword_reply",
        "location": "Religious",
        "sources": ["facebook", "whatsapp"],
        "match_mode": mode,
        "keywords": keywords or [KW],
        "reply": reply,
        "skip_media": True,
        "skip_if_human": True,
        "skip_if_hold": True,
    }


def ctx_for(chat_id, message, source="Facebook", sender="psid-builder-1", location="Religious"):
    return {
        "now": datetime.utcnow().isoformat(),
        "event": {
            "type": "message_received",
            "payload": {
                "chat_id": chat_id,
                "message_body": message,
                "source": source,
                "sender_identifier": sender,
                "location": location,
                "receiving_phone_id": "",
            },
        },
        "vars": {},
        "workflow": {"id": f"visual_test_{chat_id}", "name": "Visual Test - Religious - ديني"},
    }


# --- matching helpers ---
check("normalize_strips_emoji", normalize_keyword_text(KW) == "الراحة والقرب من الحرم", normalize_keyword_text(KW))
check("exact_equal", keyword_matches(KW, [KW], "exact") == KW)
check("exact_no_emoji", keyword_matches("الراحة والقرب من الحرم", [KW], "exact") == KW)
check("exact_rejects_extra_words", keyword_matches(f"ابعت {KW}", [KW], "exact") is None)
check("phrase_literal_in_sentence", keyword_matches(f"ابعت {KW}", [KW], "phrase") == KW)
check("phrase_rejects_plain_sentence", keyword_matches("عايز أعرف الراحة فقط", [KW], "phrase") is None)
check("contains_normalized", keyword_matches("عايز الراحة والقرب من الحرم دلوقت", [KW], "contains") == KW)
check("skip_audio", is_non_text_media_message("[Customer sent an audio message. Duration: 3s]"))

# --- engine step ---
engine = AutomationEngine(MockAgent())

agent = MockAgent()
engine.agent = agent
c = ctx_for("vb-exact-1", KW)
engine._step_keyword_reply(step_for("phrase"), c)
check("phrase_fb_sent", agent.sent and agent.sent[0][0] == "facebook" and agent.sent[0][2] == REPLY, str(agent.sent))
check("phrase_marked_live", bool(agent.live), str(agent.live))
check("phrase_vars_sent", c["vars"].get("_workflow_sent") is True, str(c.get("vars")))

agent = MockAgent()
engine.agent = agent
try:
    engine._step_keyword_reply(step_for("phrase"), ctx_for("vb-skip-hurghada", KW, location="Hurghada"))
    check("skip_other_dept", False, "expected StopWorkflow")
except StopWorkflow as e:
    check("skip_other_dept", "wrong_location" in str(e), str(e))
check("skip_other_dept_no_send", len(agent.sent) == 0, str(agent.sent))

agent = MockAgent()
engine.agent = agent
try:
    engine._step_keyword_reply(step_for("phrase"), ctx_for("vb-skip-email", KW, source="Email", sender="a@b.com"))
    check("skip_email", False, "expected StopWorkflow")
except StopWorkflow as e:
    check("skip_email", "unsupported_source" in str(e), str(e))

agent = MockAgent()
engine.agent = agent
try:
    engine._step_keyword_reply(step_for("exact"), ctx_for("vb-exact-sentence", f"ابعت {KW}"))
    check("exact_sentence_no_send", False, "expected StopWorkflow")
except StopWorkflow as e:
    check("exact_sentence_no_send", "no_match" in str(e), str(e))

agent = MockAgent()
engine.agent = agent
c = ctx_for("vb-wa-1", KW, source="WhatsApp", sender="201000000001")
engine._step_keyword_reply(step_for("phrase"), c)
check("whatsapp_channel", agent.sent and agent.sent[0][0] == "whatsapp", str(agent.sent))

# dedup: second identical message on same workflow/chat must not send
agent = MockAgent()
engine.agent = agent
c1 = ctx_for("vb-dedup-1", KW)
engine._step_keyword_reply(step_for("phrase"), c1)
try:
    engine._step_keyword_reply(step_for("phrase"), ctx_for("vb-dedup-1", KW))
    check("dedup_second", False, "expected StopWorkflow")
except StopWorkflow as e:
    check("dedup_second", "already_processed" in str(e), str(e))
check("dedup_one_send", len(agent.sent) == 1, f"sent={len(agent.sent)}")

agent = MockAgent()
engine.agent = agent
try:
    engine._step_keyword_reply(
        step_for("phrase"),
        ctx_for("vb-media", "[Customer sent an audio message. Duration: 4s]"),
    )
    check("skip_media", False, "expected StopWorkflow")
except StopWorkflow as e:
    check("skip_media", "non_text_media" in str(e), str(e))

failed = 0
for name, ok, detail in results:
    mark = "PASS" if ok else "FAIL"
    if not ok:
        failed += 1
    print(f"[{mark}] {name}" + (f" :: {detail}" if (detail and not ok) else ""))

print(f"\n{len(results) - failed}/{len(results)} passed")
sys.exit(1 if failed else 0)
