"""
Offer Bonus FTS
---------------
When a customer books the *second* (offer) trip, create a complimentary bonus
booking record linked by phone to their earlier matching booking.

Match rule:
  second.ProductID == route.offer_product_id
  AND prior booking with same phone has ProductID == route.first (booked) id
  AND no FTS-BONUS record already exists for that phone + bonus product
"""

from __future__ import annotations

import logging
import random
import re
import string
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set


from airtable_fields import FieldIds, ID_TO_READABLE_NAME
from offer_send_fts import (
    DEFAULT_OFFER_PRODUCTS,
    DEFAULT_OFFER_ROUTES,
    _clean_phone,
    _clean_str,
    _extract_product_id,
    get_product_display_name,
)

BONUS_BOOKING_PREFIX = "FTS-BONUS-"
BONUS_MARKER = "[BONUS_CREATED:"


def _readable(field_id: str, fallback: str = "") -> str:
    return ID_TO_READABLE_NAME.get(field_id) or fallback


def build_offer_trigger_index(
    routes: Optional[Dict[str, Dict[str, str]]] = None,
) -> Dict[str, List[Dict[str, str]]]:
    """
    offer_product_id -> [{first_product_id, bonus_product_id}, ...]
    """
    route_map = routes if isinstance(routes, dict) and routes else DEFAULT_OFFER_ROUTES
    out: Dict[str, List[Dict[str, str]]] = {}
    for first_pid, cfg in (route_map or {}).items():
        first_pid = _extract_product_id(first_pid)
        offer_pid = _extract_product_id((cfg or {}).get("offer_product_id"))
        bonus_pid = _extract_product_id((cfg or {}).get("bonus_product_id"))
        if not first_pid or not offer_pid or not bonus_pid:
            continue
        out.setdefault(offer_pid, []).append(
            {
                "first_product_id": first_pid,
                "bonus_product_id": bonus_pid,
            }
        )
    return out


def _generate_bonus_booking_nr() -> str:
    stamp = datetime.now(timezone.utc).strftime("%y%m%d")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"{BONUS_BOOKING_PREFIX}{stamp}-{suffix}"


def _phone_formula(phone: str) -> str:
    """Airtable formula fragment that matches Customer Phone flexibly."""
    digits = _clean_phone(phone)
    if not digits:
        return ""
    db_phone = "SUBSTITUTE(SUBSTITUTE(SUBSTITUTE({Customer Phone}&'', ' ', ''), '-', ''), '+', '')"
    parts = [f"SEARCH('{digits}', {db_phone})"]
    if len(digits) >= 8:
        parts.append(f"SEARCH('{digits[-8:]}', {db_phone})")
    if len(digits) >= 10:
        parts.append(f"SEARCH('{digits[-10:]}', {db_phone})")
    return "OR(" + ",".join(parts) + ")"


def _get_field(agent, fields: Dict[str, Any], field_id: str, *name_fallbacks: str) -> Any:
    val = None
    try:
        val = agent.get_field_value(fields, field_id)
    except Exception:
        val = None
    if val is not None and _clean_str(val) != "":
        return val
    for name in name_fallbacks:
        if name in fields and fields.get(name) is not None and _clean_str(fields.get(name)) != "":
            return fields.get(name)
    readable = _readable(field_id)
    if readable and readable in fields:
        return fields.get(readable)
    return None


def _record_product_id(agent, fields: Dict[str, Any]) -> str:
    return _extract_product_id(_get_field(agent, fields, FieldIds.PRODUCT_ID, "Product ID"))


def _record_phone(agent, fields: Dict[str, Any]) -> str:
    return _clean_phone(_get_field(agent, fields, FieldIds.CUSTOMER_PHONE, "Customer Phone"))


def _record_booking_nr(agent, fields: Dict[str, Any]) -> str:
    return _clean_str(_get_field(agent, fields, FieldIds.BOOKING_NR, "Booking Nr."))


def _remarks_has_bonus_marker(remarks: Any) -> bool:
    return BONUS_MARKER in _clean_str(remarks)


def _find_records_by_phone(agent, phone: str, max_records: int = 50) -> List[Dict[str, Any]]:
    phone_f = _phone_formula(phone)
    if not phone_f:
        return []
    formula = f"AND({{Customer Phone}}!='', {phone_f})"
    try:
        return list(
            agent.table.all(
                formula=formula,
                max_records=max_records,
            )
            or []
        )
    except Exception as e:
        logging.warning(f"Offer bonus phone lookup failed: {e}")
        return []


def _find_prior_first_booking(
    agent,
    phone: str,
    first_product_ids: Set[str],
    exclude_record_id: str,
) -> Optional[Dict[str, Any]]:
    for rec in _find_records_by_phone(agent, phone):
        rid = _clean_str((rec or {}).get("id"))
        if not rid or rid == exclude_record_id:
            continue
        fields = (rec or {}).get("fields") or {}
        booking_nr = _record_booking_nr(agent, fields)
        if booking_nr.startswith(BONUS_BOOKING_PREFIX):
            continue
        pid = _record_product_id(agent, fields)
        if pid and pid in first_product_ids:
            return rec
    return None


def _bonus_already_exists(agent, phone: str, bonus_product_id: str) -> bool:
    phone_f = _phone_formula(phone)
    pid = _extract_product_id(bonus_product_id)
    if not phone_f or not pid:
        return False
    formula = (
        f"AND("
        f"{{Customer Phone}}!='',"
        f"{phone_f},"
        f"OR("
        f"FIND('{BONUS_BOOKING_PREFIX}', {{Booking Nr.}}&''),"
        f"FIND('{pid}', {{Product ID}}&'')"
        f")"
        f")"
    )
    try:
        rows = list(agent.table.all(formula=formula, max_records=30) or [])
    except Exception as e:
        logging.warning(f"Offer bonus existence check failed: {e}")
        return False
    for rec in rows:
        fields = (rec or {}).get("fields") or {}
        bn = _record_booking_nr(agent, fields)
        existing_pid = _record_product_id(agent, fields)
        if bn.startswith(BONUS_BOOKING_PREFIX) and existing_pid == pid:
            return True
        # Bonus product record that was auto-created (remarks marker)
        if existing_pid == pid and _remarks_has_bonus_marker(
            _get_field(agent, fields, FieldIds.REMARKS, "Remarks")
        ):
            return True
    return False


def _copy_value(agent, fields: Dict[str, Any], field_id: str, *names: str) -> Any:
    return _get_field(agent, fields, field_id, *names)


def _build_bonus_fields(
    agent,
    first_fields: Dict[str, Any],
    second_fields: Dict[str, Any],
    bonus_product_id: str,
    bonus_name: str,
    bonus_booking_nr: str,
    first_booking_nr: str,
    second_booking_nr: str,
) -> Dict[str, Any]:
    """Duplicate customer details; trip = bonus; no Date Trip."""

    def from_either(field_id: str, *names: str, prefer_second: bool = False) -> Any:
        if prefer_second:
            v = _copy_value(agent, second_fields, field_id, *names)
            if v is not None and _clean_str(v) != "":
                return v
            return _copy_value(agent, first_fields, field_id, *names)
        v = _copy_value(agent, first_fields, field_id, *names)
        if v is not None and _clean_str(v) != "":
            return v
        return _copy_value(agent, second_fields, field_id, *names)

    fields_out: Dict[str, Any] = {
        _readable(FieldIds.BOOKING_NR, "Booking Nr."): bonus_booking_nr,
        _readable(FieldIds.PRODUCT_ID, "Product ID"): bonus_product_id,
        _readable(FieldIds.TRIP_NAME, "trip Name"): bonus_name,
        _readable(FieldIds.REAL_PRODUCT_NAME, "Real Product Name"): bonus_name,
        _readable(FieldIds.CUSTOMER_NAME, "Customer Name"): from_either(
            FieldIds.CUSTOMER_NAME, "Customer Name"
        ),
        _readable(FieldIds.CUSTOMER_PHONE, "Customer Phone"): from_either(
            FieldIds.CUSTOMER_PHONE, "Customer Phone", prefer_second=True
        ),
        _readable(FieldIds.CUSTOMER_EMAIL, "Customer Email"): from_either(
            FieldIds.CUSTOMER_EMAIL, "Customer Email"
        ),
        _readable(FieldIds.CUSTOMER_PERSONAL_EMAIL, "Customer personal email"): from_either(
            FieldIds.CUSTOMER_PERSONAL_EMAIL, "Customer personal email"
        ),
        _readable(FieldIds.HOTEL_NAME, "Hotel Name"): from_either(
            FieldIds.HOTEL_NAME, "Hotel Name", prefer_second=True
        ),
        _readable(FieldIds.ROOM_NUMBER, "Room number"): from_either(
            FieldIds.ROOM_NUMBER, "Room number", "Room Number", prefer_second=True
        ),
        _readable(FieldIds.DES, "des"): from_either(FieldIds.DES, "des", "Des"),
        _readable(FieldIds.AGENCY, "Agency"): "FTS Bonus",
        _readable(FieldIds.REMARKS, "Remarks"): (
            f"{BONUS_MARKER}{bonus_booking_nr}] Auto complimentary bonus. "
            f"First booking: {first_booking_nr or '-'}. "
            f"Second (offer) booking: {second_booking_nr or '-'}. "
            f"Date Trip left empty for operations to set with customer."
        ),
        _readable(FieldIds.NOTE, "Note"): (
            f"Complimentary bonus for cross-sell. "
            f"Linked phone match. Offer booking {second_booking_nr or '-'}."
        ),
    }

    for fid, names in (
        (FieldIds.ADT, ("ADT",)),
        (FieldIds.STD, ("STD",)),
        (FieldIds.CHD, ("CHD",)),
        (FieldIds.INF, ("Inf", "INF")),
        (FieldIds.TOTAL_TRAVELERS, ("Total Travelers", "Total travelers")),
    ):
        val = from_either(fid, *names, prefer_second=True)
        if val is not None and _clean_str(val) != "":
            fields_out[_readable(fid, names[0])] = val

    return {k: v for k, v in fields_out.items() if v is not None and _clean_str(v) != ""}


def _mark_second_booking(agent, record_id: str, bonus_booking_nr: str, dry_run: bool) -> bool:
    if dry_run or not record_id:
        return False
    try:
        rec = agent.table.get(record_id)
        fields = (rec or {}).get("fields") or {}
        remarks_key = _readable(FieldIds.REMARKS, "Remarks")
        old = _clean_str(fields.get(remarks_key) or fields.get("Remarks"))
        marker = f"{BONUS_MARKER}{bonus_booking_nr}]"
        if marker in old:
            return True
        new_remarks = f"{old} | {marker}".strip(" |") if old else marker
        agent.update_booking_record(record_id, {remarks_key: new_remarks})
        return True
    except Exception as e:
        logging.warning(f"Failed marking second booking {record_id}: {e}")
        return False


def _fetch_candidate_seconds(
    agent,
    offer_product_ids: Set[str],
    view: str,
    max_records: int,
) -> List[Dict[str, Any]]:
    view = _clean_str(view)
    if view:
        try:
            return list(agent.table.all(view=view, max_records=max_records) or [])
        except Exception as e:
            logging.warning(f"Offer bonus view fetch failed ({view}): {e}")

    # Fallback: formula on known offer product ids
    if not offer_product_ids:
        return []
    bits = [f"FIND('{pid}', {{Product ID}}&'')" for pid in sorted(offer_product_ids)]
    formula = "OR(" + ",".join(bits) + ")"
    try:
        return list(agent.table.all(formula=formula, max_records=max_records) or [])
    except Exception as e:
        logging.error(f"Offer bonus candidate fetch failed: {e}", exc_info=True)
        return []


def run(agent, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = payload or {}
    view = _clean_str(payload.get("view")) or "Offer Get Your Guide2"
    max_records = int(payload.get("max_records") or 25)
    dry_run = bool(payload.get("dry_run", True))

    route_map = DEFAULT_OFFER_ROUTES
    if isinstance(payload.get("routes"), dict) and payload.get("routes"):
        route_map = {**DEFAULT_OFFER_ROUTES, **payload["routes"]}

    product_map = DEFAULT_OFFER_PRODUCTS
    if isinstance(payload.get("products"), dict) and payload.get("products"):
        product_map = {**DEFAULT_OFFER_PRODUCTS, **payload["products"]}

    trigger_index = build_offer_trigger_index(route_map)
    offer_ids = set(trigger_index.keys())

    candidates = _fetch_candidate_seconds(agent, offer_ids, view, max_records)
    results: List[Dict[str, Any]] = []
    created = 0
    skipped = 0

    for rec in candidates:
        rid = _clean_str((rec or {}).get("id"))
        fields = (rec or {}).get("fields") or {}
        if not rid:
            continue

        second_pid = _record_product_id(agent, fields)
        phone = _record_phone(agent, fields)
        second_bn = _record_booking_nr(agent, fields)

        if second_bn.startswith(BONUS_BOOKING_PREFIX):
            skipped += 1
            results.append({"record_id": rid, "status": "skipped", "message": "is_bonus_record"})
            continue

        if second_pid not in offer_ids:
            skipped += 1
            results.append(
                {
                    "record_id": rid,
                    "status": "skipped",
                    "booking_nr": second_bn,
                    "product_id": second_pid,
                    "message": "not_offer_product",
                }
            )
            continue

        if _remarks_has_bonus_marker(_get_field(agent, fields, FieldIds.REMARKS, "Remarks")):
            skipped += 1
            results.append(
                {
                    "record_id": rid,
                    "status": "skipped",
                    "booking_nr": second_bn,
                    "message": "already_marked_bonus_created",
                }
            )
            continue

        if not phone:
            skipped += 1
            results.append(
                {
                    "record_id": rid,
                    "status": "error",
                    "booking_nr": second_bn,
                    "message": "missing_phone",
                }
            )
            continue

        pairs = trigger_index.get(second_pid) or []
        first_ids = {_extract_product_id(p.get("first_product_id")) for p in pairs}
        first_ids = {x for x in first_ids if x}
        # All pairs for same offer share same bonus in our table, take first bonus id
        bonus_pid = _extract_product_id((pairs[0] or {}).get("bonus_product_id")) if pairs else ""
        if not bonus_pid or not first_ids:
            skipped += 1
            results.append(
                {
                    "record_id": rid,
                    "status": "skipped",
                    "booking_nr": second_bn,
                    "message": "incomplete_route",
                }
            )
            continue

        prior = _find_prior_first_booking(agent, phone, first_ids, exclude_record_id=rid)
        if not prior:
            skipped += 1
            results.append(
                {
                    "record_id": rid,
                    "status": "skipped",
                    "booking_nr": second_bn,
                    "phone": phone,
                    "offer_product_id": second_pid,
                    "message": "no_matching_first_booking_by_phone",
                }
            )
            continue

        prior_fields = (prior or {}).get("fields") or {}
        prior_bn = _record_booking_nr(agent, prior_fields)
        prior_pid = _record_product_id(agent, prior_fields)

        if _bonus_already_exists(agent, phone, bonus_pid):
            skipped += 1
            # Still mark second booking if unmarked
            results.append(
                {
                    "record_id": rid,
                    "status": "skipped",
                    "booking_nr": second_bn,
                    "message": "bonus_already_exists",
                    "first_booking_nr": prior_bn,
                    "bonus_product_id": bonus_pid,
                }
            )
            continue

        bonus_name = get_product_display_name(bonus_pid, product_map, fallback=f"Bonus {bonus_pid}")
        bonus_name = _clean_str(bonus_name) or f"Bonus {bonus_pid}"
        if "free" not in bonus_name.lower():
            bonus_name = f"{bonus_name} FREE"

        bonus_bn = _generate_bonus_booking_nr()
        create_fields = _build_bonus_fields(
            agent,
            prior_fields,
            fields,
            bonus_pid,
            bonus_name,
            bonus_bn,
            prior_bn,
            second_bn,
        )

        if dry_run:
            results.append(
                {
                    "record_id": rid,
                    "status": "dry_run",
                    "booking_nr": second_bn,
                    "phone": phone,
                    "first_booking_nr": prior_bn,
                    "first_product_id": prior_pid,
                    "offer_product_id": second_pid,
                    "bonus_product_id": bonus_pid,
                    "bonus_booking_nr": bonus_bn,
                    "bonus_trip_name": bonus_name,
                    "create_fields": create_fields,
                }
            )
            continue

        try:
            created_rec = agent.table.create(create_fields, typecast=True)
            created_id = _clean_str((created_rec or {}).get("id"))
            _mark_second_booking(agent, rid, bonus_bn, dry_run=False)
            created += 1
            results.append(
                {
                    "record_id": rid,
                    "status": "success",
                    "booking_nr": second_bn,
                    "phone": phone,
                    "first_booking_nr": prior_bn,
                    "first_product_id": prior_pid,
                    "offer_product_id": second_pid,
                    "bonus_product_id": bonus_pid,
                    "bonus_booking_nr": bonus_bn,
                    "bonus_record_id": created_id,
                    "bonus_trip_name": bonus_name,
                }
            )
        except Exception as e:
            logging.error(f"Offer bonus create failed for {second_bn}: {e}", exc_info=True)
            results.append(
                {
                    "record_id": rid,
                    "status": "error",
                    "booking_nr": second_bn,
                    "message": f"create_failed: {e}",
                }
            )

    return {
        "status": "success",
        "data": {
            "view": view,
            "dry_run": dry_run,
            "offer_product_ids": sorted(offer_ids),
            "processed": len(results),
            "created": created,
            "skipped": skipped,
            "results": results,
        },
    }
