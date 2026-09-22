# -*- coding: utf-8 -*-
"""Religious Contact keyword → tag rules.

Managers define tags and keywords in Contact (Religious). When a customer
message contains a keyword, the contact is tagged in sales_customer_state.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fts_paths import get_data_path

log = logging.getLogger("ReligiousContactTagRules")

CONFIG_FILE = get_data_path("religious_contact_tag_rules.json")

DEFAULT_RULES = [
    {
        "id": "default-not-interested",
        "tag": "غير مهتم",
        "keywords": [
            "غير مهتم",
            "مش مهتم",
            "مش عاوز",
            "مش عايز",
            "شكرا مش عاوز",
            "شكرا مش عايز",
            "شكرا مش مهتم",
            "شكرا غير مهتم",
        ],
        "enabled": True,
        "match": "contains",
    }
]


def _utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _normalize(text: str) -> str:
    try:
        s = str(text or "").strip().lower()
        s = re.sub(r"[\u0610-\u061A\u0640\u064B-\u065F\u0670\u06D6-\u06ED]", "", s)
        # Arabic alef / teh marbuta variants
        s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
        s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
        s = re.sub(r"\s+", " ", s, flags=re.UNICODE)
        return s.strip()
    except Exception:
        return str(text or "").strip().lower()


def _default_config() -> dict:
    return {
        "version": 1,
        "updated_at": _utc_now(),
        "rules": list(DEFAULT_RULES),
    }


def load_config() -> dict:
    try:
        if CONFIG_FILE and __import__("os").path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            if not isinstance(data, dict):
                return _default_config()
            rules = data.get("rules")
            if not isinstance(rules, list):
                data["rules"] = list(DEFAULT_RULES)
            return data
    except Exception as e:
        log.warning("Failed to load contact tag rules: %s", e)
    return _default_config()


def save_config(config: dict) -> dict:
    cleaned = sanitize_config(config)
    cleaned["updated_at"] = _utc_now()
    cleaned["version"] = int(cleaned.get("version") or 1)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
    return cleaned


def sanitize_config(config: Any) -> dict:
    src = config if isinstance(config, dict) else {}
    rules_in = src.get("rules") if isinstance(src.get("rules"), list) else []
    rules_out: List[dict] = []
    seen_ids = set()
    for raw in rules_in:
        if not isinstance(raw, dict):
            continue
        tag = str(raw.get("tag") or "").strip()
        if not tag:
            continue
        keywords = []
        for kw in (raw.get("keywords") if isinstance(raw.get("keywords"), list) else []):
            s = str(kw or "").strip()
            if s and s not in keywords:
                keywords.append(s)
        if not keywords:
            continue
        rid = str(raw.get("id") or "").strip() or str(uuid.uuid4())
        if rid in seen_ids:
            rid = str(uuid.uuid4())
        seen_ids.add(rid)
        match_mode = str(raw.get("match") or "contains").strip().lower()
        if match_mode not in ("contains", "exact"):
            match_mode = "contains"
        rules_out.append(
            {
                "id": rid,
                "tag": tag,
                "keywords": keywords,
                "enabled": bool(raw.get("enabled", True)),
                "match": match_mode,
            }
        )
    return {
        "version": int(src.get("version") or 1),
        "updated_at": str(src.get("updated_at") or _utc_now()),
        "rules": rules_out,
    }


def list_rules() -> List[dict]:
    return list(load_config().get("rules") or [])


def match_message(message_body: str, rules: Optional[List[dict]] = None) -> Optional[dict]:
    """Return the first matching rule (prefer longer keywords)."""
    normalized_message = _normalize(message_body)
    if not normalized_message:
        return None
    candidates: List[Tuple[int, dict, str]] = []
    for rule in (rules if rules is not None else list_rules()):
        if not rule or not rule.get("enabled", True):
            continue
        tag = str(rule.get("tag") or "").strip()
        if not tag:
            continue
        match_mode = str(rule.get("match") or "contains").strip().lower()
        for kw in rule.get("keywords") or []:
            nkw = _normalize(str(kw or ""))
            if not nkw:
                continue
            hit = False
            if match_mode == "exact":
                hit = normalized_message == nkw
            else:
                hit = nkw in normalized_message
            if hit:
                candidates.append((len(nkw), rule, str(kw)))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    rule, keyword = candidates[0][1], candidates[0][2]
    return {"rule": rule, "keyword": keyword, "tag": rule.get("tag")}


def _parse_tags(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    s = str(raw).strip()
    if not s:
        return []
    if s.startswith("["):
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except Exception:
            pass
    # Contact UI often stores a single free-text tag
    if "," in s and not s.startswith("["):
        parts = [p.strip() for p in s.split(",") if p.strip()]
        if parts:
            return parts
    return [s]


def format_tags_display(raw: Any) -> str:
    tags = _parse_tags(raw)
    return ", ".join(tags)


def apply_tag_to_chat(chat_id: str, tag: str) -> dict:
    """Set/merge tag on sales_customer_state. Returns {ok, tags, added}."""
    chat_id = str(chat_id or "").strip()
    tag = str(tag or "").strip()
    if not chat_id or not tag:
        return {"ok": False, "error": "missing_chat_id_or_tag"}
    try:
        import chat_db

        existing = chat_db.get_sales_state(chat_id) or {}
        tags = _parse_tags(existing.get("tags"))
        added = False
        if tag not in tags:
            # Contact UX is primarily one active classification tag.
            # Keep previous tags, put the matched tag first for visibility.
            tags = [tag] + [t for t in tags if t != tag]
            added = True
        tags_json = json.dumps(tags, ensure_ascii=False)
        # Also keep a plain primary tag string friendly for Contact filters:
        # store JSON list (workflows already use this). Display layer formats it.
        res = chat_db.upsert_sales_state(chat_id=chat_id, updates={"tags": tags_json})
        if not res.get("ok"):
            return {"ok": False, "error": res.get("error") or "upsert_failed"}
        return {"ok": True, "tags": tags, "added": added, "display": format_tags_display(tags)}
    except Exception as e:
        log.exception("apply_tag_to_chat failed")
        return {"ok": False, "error": str(e)}


def apply_rules_to_message(chat_id: str, message_body: str, location: str = "") -> dict:
    loc = str(location or "").strip().lower()
    if loc and loc != "religious":
        return {"ok": True, "skipped": "not_religious"}
    matched = match_message(message_body)
    if not matched:
        return {"ok": True, "matched": False}
    tag = str(matched.get("tag") or "").strip()
    result = apply_tag_to_chat(chat_id, tag)
    result["matched"] = True
    result["keyword"] = matched.get("keyword")
    result["rule_id"] = (matched.get("rule") or {}).get("id")
    return result


def register_routes(app, agent=None):
    from flask import jsonify, request

    def _ok_options():
        return jsonify({"status": "ok"}), 200

    @app.route("/api/religious/contact_tag_rules", methods=["GET", "PUT", "OPTIONS"])
    def api_religious_contact_tag_rules():
        if request.method == "OPTIONS":
            return _ok_options()
        try:
            if request.method == "GET":
                cfg = load_config()
                return jsonify({"status": "success", "data": cfg}), 200
            payload = request.get_json(silent=True) or {}
            # Accept either full config or {rules: [...]}
            if "rules" in payload:
                cfg = save_config(payload)
            else:
                return jsonify({"status": "error", "message": "rules array required"}), 400
            return jsonify({"status": "success", "data": cfg}), 200
        except Exception as e:
            log.exception("contact_tag_rules")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/api/religious/contact_tag_rules/test", methods=["POST", "OPTIONS"])
    def api_religious_contact_tag_rules_test():
        if request.method == "OPTIONS":
            return _ok_options()
        try:
            payload = request.get_json(silent=True) or {}
            text = str(payload.get("message") or payload.get("text") or "")
            matched = match_message(text)
            return jsonify(
                {
                    "status": "success",
                    "matched": bool(matched),
                    "data": matched,
                }
            ), 200
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
