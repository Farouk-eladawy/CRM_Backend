# -*- coding: utf-8 -*-
"""
Workflow: Religious Contact keyword → auto-tag (Contact tab rules).

Reads rules from religious_contact_tag_rules.json (managed in Contact UI).
When a Religious customer message contains a configured keyword, the contact
is tagged in sales_customer_state. No auto-reply is sent.
"""

from __future__ import annotations

import logging

log = logging.getLogger("ReligiousContactKeywordTag")


def run(agent, payload: dict = None) -> dict:
    payload = payload or {}
    chat_id = str(payload.get("chat_id") or "").strip()
    message_body = str(payload.get("message_body") or "").strip()
    location = str(payload.get("location") or "").strip()
    source = str(payload.get("source") or "").strip()

    if location.lower() != "religious":
        return {"ok": True, "skipped": "not_religious", "chat_id": chat_id}

    if source.lower() not in ("facebook", "whatsapp", ""):
        return {"ok": True, "skipped": "unsupported_source", "chat_id": chat_id}

    if not chat_id or not message_body:
        return {"ok": True, "skipped": "missing_fields", "chat_id": chat_id}

    # Skip non-text media placeholders
    lb = message_body.lower().strip()
    if lb.startswith("[customer sent") or lb.startswith("[customer shared"):
        return {"ok": True, "skipped": "media", "chat_id": chat_id}

    try:
        from religious_contact_tag_rules import apply_rules_to_message

        result = apply_rules_to_message(chat_id, message_body, location=location)
        if result.get("matched") and result.get("ok"):
            log.info(
                "Tagged chat %s as '%s' (keyword=%s)",
                chat_id,
                result.get("tags") or result.get("display"),
                result.get("keyword"),
            )
            try:
                import chat_db

                chat_db.add_message(
                    chat_id,
                    "agent",
                    f"[System Log] Contact auto-tag: {result.get('display') or ''} (keyword: {result.get('keyword') or ''})",
                    status="sent",
                    source="System",
                )
            except Exception:
                pass
        return {"ok": True, "chat_id": chat_id, **result}
    except Exception as e:
        log.exception("contact keyword tag failed")
        return {"ok": False, "error": str(e), "chat_id": chat_id}
