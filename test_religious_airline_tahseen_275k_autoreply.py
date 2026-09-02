# -*- coding: utf-8 -*-
"""Dry-run harness: simulates run() end-to-end with mock send/log (no real send, no prod writes)."""
import sys, io, os, types, tempfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

import chat_db
# Patch chat_db functions used by the workflow in THIS process only (throwaway) -> no prod DB writes.
chat_db.add_message = lambda **kw: print("    [log] add_message:", kw.get("status"), "| len(text)=", len(kw.get("text") or ""), "| source=", kw.get("source"))
chat_db.mark_conversation_read = lambda *a, **k: print("    [log] mark_conversation_read")
chat_db.delete_proposed_drafts = lambda *a, **k: print("    [log] delete_proposed_drafts")
chat_db.get_conversation = lambda chat_id: {}   # needs_help=0, no hold
chat_db.update_auto_reply_hold_until = lambda *a, **k: None
chat_db.get_cairo_time = lambda: "2026-09-02T16:00:00+03:00"

mod = types.ModuleType("wf_mod")
code = open(os.path.join(ROOT, "workflows", "religious_airline_tahseen_275k_autoreply.py"), encoding="utf-8").read()
exec(compile(code, "religious_airline_tahseen_275k_autoreply.py", "exec"), mod.__dict__)

sent = []
def fake_send(agent, text, source, sender_identifier, location, receiving_phone_id, chat_id):
    sent.append(text)
    print(f"    [SEND] chat={chat_id} src={source} -> len={len(text)} | preview: {text[:60]}...")
    return ("Facebook", True, None)
mod._send_one = fake_send
# redirect dedup DB to a temp file so the real dedup db is untouched
tmp_db = os.path.join(tempfile.gettempdir(), "tahseen275k_test_dedup.db")
if os.path.exists(tmp_db):
    os.remove(tmp_db)
mod.DEDUP_DB = tmp_db
mod.STATE_FILE = os.path.join(tempfile.gettempdir(), "tahseen275k_test_state.json")
if os.path.exists(mod.STATE_FILE):
    os.remove(mod.STATE_FILE)

class MockAgent:
    def send_whatsapp_message(self, *a, **k): return True, None
    def send_facebook_message(self, *a, **k): return True, None
    def cancel_whatsapp_ai_processing(self, **k): print("    [log] cancel_whatsapp_ai_processing")
agent = MockAgent()

def payload(msg, loc="Religious", chat="test_chat_1", src="facebook"):
    return {"chat_id": chat, "message_body": msg, "source": src,
            "sender_identifier": "psid_test", "location": loc,
            "receiving_phone_id": None, "incoming_external_message_id": "mid_test"}

print("=== CASE 1: Religious + exact keyword (expect 2 sends) ===")
r = mod.run(agent, payload("طيران تحسين — ٢٧٥ ألف"))
print("result:", {k: r[k] for k in r if k != "reply_preview"})

print("\n=== CASE 2: same msg again -> dedup (expect skip already_processed) ===")
r = mod.run(agent, payload("طيران تحسين — ٢٧٥ ألف"))
print("result:", r)

print("\n=== CASE 3: other location Hurghada (expect not_religious) ===")
r = mod.run(agent, payload("طيران تحسين — ٢٧٥ ألف", loc="Hurghada"))
print("result:", r)

print("\n=== CASE 4: partial text (expect no_keyword_match) ===")
r = mod.run(agent, payload("طيران تحسين ايه مميزاته", chat="test_chat_2"))
print("result:", r)

print("\n=== CASE 5: different chat exact keyword (expect 2 sends) ===")
r = mod.run(agent, payload("طيران تحسين — ٢٧٥ ألف؟", chat="test_chat_3"))
print("result:", {k: r[k] for k in r if k != "reply_preview"})

print("\n=== CASE 6: whatsapp source send path (expect WhatsApp channel) ===")
mod.DEDUP_DB = os.path.join(tempfile.gettempdir(), "tahseen275k_test_dedup_wa.db")
if os.path.exists(mod.DEDUP_DB):
    os.remove(mod.DEDUP_DB)
def fake_send_wa(agent, text, source, sender_identifier, location, receiving_phone_id, chat_id):
    sent.append(text)
    print(f"    [SEND-WA] {sender_identifier} -> len={len(text)}")
    return ("WhatsApp", True, None)
mod._send_one = fake_send_wa
r = mod.run(agent, payload("طيران تحسين — ٢٧٥ ألف", chat="test_chat_4", src="whatsapp", ) | {"sender_identifier": "2010xxxx"})
print("result:", {k: r[k] for k in r if k != "reply_preview"})

print("\nTotal simulated sends:", len(sent))
print("=== DRY-RUN COMPLETE ===")
