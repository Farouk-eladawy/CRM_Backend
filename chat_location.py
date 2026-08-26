"""Shared inbox routing helpers derived from Airtable destination (des)."""

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
