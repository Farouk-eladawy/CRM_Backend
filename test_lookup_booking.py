import json
import re

from pyairtable import Api


def mask_email(email: str) -> str:
    email = str(email or "").strip()
    if not email:
        return ""
    if "@" not in email:
        return (email[:2] + "***") if len(email) >= 2 else "***"
    user, domain = email.split("@", 1)
    if not user:
        return "***@" + domain
    return user[:2] + "***@" + domain


def mask_phone(phone: str) -> str:
    phone = str(phone or "").strip()
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 6:
        return (phone[:2] + "***") if len(phone) >= 2 else "***"
    return f"+{digits[:2]}***{digits[-2:]}"


def main():
    with open("config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)

    api = Api(cfg["airtable"]["api_key"])
    table = api.table(cfg["airtable"]["base_id"], cfg["airtable"]["tables"]["main_list"])

    booking_nr = "12345Test"
    records = table.all(formula=f"{{Booking Nr.}}='{booking_nr}'")

    print("booking_nr:", booking_nr)
    print("matches:", len(records))
    for r in records[:5]:
        f = (r or {}).get("fields", {}) or {}
        email = f.get("Customer personal email") or f.get("Customer Email") or ""
        phone = f.get("Customer Phone") or ""
        print("---")
        print("record_id:", r.get("id"))
        print("Customer Name:", str(f.get("Customer Name") or "")[:60])
        print("Email:", mask_email(email))
        print("Phone:", mask_phone(phone))
        print("Amount:", f.get("Amount"))
        print("Currency:", f.get("Currency"))


if __name__ == "__main__":
    main()

