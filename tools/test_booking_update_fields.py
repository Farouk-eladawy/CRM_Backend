import json
import requests


API_BASE = "https://api.ftstravels.com/api"


def find_record_by_booking_nr(booking_nr: str, view: str = "Booking_Weekly", page_limit: int = 25):
    offset = None
    for _ in range(page_limit):
        url = f"{API_BASE}/operations/bookings?view={view}"
        if offset:
            url += f"&offset={requests.utils.quote(offset)}"
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        payload = r.json()
        if payload.get("status") != "success":
            raise RuntimeError(payload)
        for rec in payload.get("data") or []:
            f = rec.get("fields") or {}
            if str(f.get("Booking Nr.") or "").strip() == booking_nr:
                return rec
        offset = payload.get("offset")
        if not offset:
            break
    return None


def normalize_numeric(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return None
    cleaned = "".join(ch for ch in s if ch.isdigit() or ch in ".-")
    try:
        return float(cleaned)
    except Exception:
        return None


def test_update(record_id: str, field: str, value, actor=None, field_type=None):
    body = {
        "record_id": record_id,
        "fields": {field: value},
        "actor": actor or {"id": "system", "name": "SchemaTest"},
        "field_types": {field: field_type} if field_type else {},
    }
    r = requests.post(f"{API_BASE}/operations/update_booking", json=body, timeout=30)
    try:
        payload = r.json()
    except Exception:
        payload = {"raw": r.text}
    return r.status_code, payload


def resolve_field_key(fields: dict, wanted: str):
    if wanted in fields:
        return wanted
    w = str(wanted).strip()
    for k in fields.keys():
        if str(k).strip() == w:
            return k
    return wanted


def main():
    booking_nr = "12345Test1"
    record = find_record_by_booking_nr(booking_nr)
    if not record:
        print(f"Booking not found: {booking_nr}")
        return

    record_id = record.get("id")
    fields = record.get("fields") or {}
    target_fields = ["Inf", "Youth", "Net Rate", "Total price USD", "Total price GBP"]

    print(f"Booking: {booking_nr}")
    print(f"Record ID: {record_id}")
    print("")

    for f in target_fields:
        key = resolve_field_key(fields, f)
        current = fields.get(key)
        print(f"- {f} ({key!r}): current={current!r}")
    print("")

    for f in target_fields:
        key = resolve_field_key(fields, f)
        current = fields.get(key)
        if current is None or current == "":
            print(f"[SKIP] {f}: empty value (no write test to avoid changing data)")
            continue
        if str(f).strip() == "Net Rate":
            value = str(current)
            field_type = "text"
        else:
            num = normalize_numeric(current)
            value = num if num is not None else current
            field_type = "number" if num is not None else "text"
        code, resp = test_update(record_id, key, value, actor={"id": "system", "name": "SchemaTest"}, field_type=field_type)
        ok = (code == 200 and resp.get("status") == "success")
        if ok:
            print(f"[OK] {f}: update accepted (sent {value!r} as {field_type})")
        else:
            msg = resp.get("message") or resp
            print(f"[FAIL] {f}: {code} {msg}")


if __name__ == "__main__":
    main()
