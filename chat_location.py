"""Shared inbox routing helpers derived from Airtable destination (des)."""

STAFF_INBOX_LOCATIONS = frozenset({"Guides", "Drivers"})


def is_staff_inbox_location(location):
    return str(location or "").strip() in STAFF_INBOX_LOCATIONS


def resolve_inbox_location(current_location, incoming_location):
    """Keep Guides/Drivers pinned; allow staff incoming to override customer inboxes."""
    incoming = str(incoming_location or "").strip()
    current = str(current_location or "").strip()
    if incoming in STAFF_INBOX_LOCATIONS:
        return incoming
    if current in STAFF_INBOX_LOCATIONS:
        return current
    if incoming and incoming.lower() not in ("unknown", "needhelp", "all"):
        if not current or current.lower() in ("unknown", ""):
            return incoming
        return current
    return current or incoming or "Unknown"


SHARM_DESTINATION_KEYS = (
    "sharm",
    "sharm el",
    "sharm el-sheikh",
    "ras mohamed",
    "dahab",
    "blue hole",
    "naama",
    "nabq",
)


def derive_chat_location_from_des(des, fallback_location="Unknown"):
    """Map Airtable des to dashboard inbox location (Sharm vs Hurghada/Cairo)."""
    if is_staff_inbox_location(fallback_location):
        return str(fallback_location).strip()
    destination_text = str(des or "").strip().lower()
    if any(key in destination_text for key in SHARM_DESTINATION_KEYS):
        return "Sharm"
    if destination_text:
        return "Hurghada/Cairo"

    fallback = str(fallback_location or "").strip()
    fallback_lower = fallback.lower()
    if any(key in fallback_lower for key in SHARM_DESTINATION_KEYS):
        return "Sharm"
    if any(
        key in fallback_lower
        for key in ("hurghada", "cairo", "giza", "luxor", "aswan", "alexandria")
    ):
        return "Hurghada/Cairo"
    if fallback in {"Sharm", "Hurghada/Cairo", "Sales", "Quality", "Unknown", "Religious"}:
        return fallback
    return "Unknown"


def extract_des_from_fields(fields):
    """Read des from Airtable fields dict (name or legacy keys)."""
    if not isinstance(fields, dict):
        return ""
    for key in ("des", "DES", "Des"):
        value = fields.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""
