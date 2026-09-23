"""Generate Airtable Products_Catalog import CSV for Tiqets LIVE products."""
import csv
from pathlib import Path

OUT = Path(__file__).resolve().parent / "tiqets_products_catalog_import.csv"

# Portal snapshot 2026-09-22 — LIVE AND SELLING only
PRODUCTS = [
    ("1116558", "Al-Hakim Mosque Cairo: Guided Tour + Roundtrip Transport", 85.00),
    ("1115845", "Amr ibn al-As Mosque: Guided Tour + Roundtrip Transfer", 85.00),
    ("1115096", "Cairo: Dinner at The Great Pyramid Inn + Transfers", 70.00),
    ("1115844", "Cairo: Guided Tour + Opera House Entry + Roundtrip Transfer", 95.00),
    (
        "1116286",
        "Cairo: Nile Crystal Dinner Cruise + Dance & Music Show + Optional Transfers",
        27.00,
    ),
    (
        "1129181",
        "Cairo: Nile Maxim Dinner Cruise + Belly Dance & Tanura + Optional Transfers",
        75.00,
    ),
    (
        "1129083",
        "Cairo: Nile Pharaohs Dinner Cruise + Optional Transfer & Drinks",
        47.80,
    ),
    (
        "1116288",
        "Egyptian Museum Cairo & National Museum of Egyptian Civilization: Private Tour",
        100.00,
    ),
    (
        "1118072",
        "Egyptian Museum Cairo, Giza Pyramids & Sphinx: Guided Tour + Transfer + Lunch",
        95.00,
    ),
    ("1115262", "Egyptian Museum Cairo: Skip The Line Ticket", 15.00),
    (
        "1118071",
        "Giza Pyramids & Sphinx: Guided Tour + Transfers + Lunch + Camel Ride",
        76.00,
    ),
    (
        "1118070",
        "Giza Pyramids & Sphinx: Half-Day Guided Tour + Roundtrip Transfer",
        55.00,
    ),
    (
        "1115884",
        "Giza Pyramids, Sphinx & National Museum: Guided Tour + Transfer + Lunch",
        130.00,
    ),
    (
        "1132517",
        "Grand Egyptian Museum: Entry Ticket + Hotel Transfers + Nile Dinner Cruise",
        110.00,
    ),
    ("1115717", "Grand Egyptian Museum: Guided Tour + Transfers", 90.00),
    ("1123804", "Grand Egyptian Museum: Skip The Line Ticket", 35.00),
    ("1132779", "Luxor Temple: Skip The Line Ticket", 13.00),
    (
        "1122152",
        "Pyramids of Giza & Grand Egyptian Museum: Entry + Transfers + Optional Guide",
        58.00,
    ),
    (
        "1121949",
        "Pyramids of Giza & The Great Pyramid: Entry Ticket + Transfers",
        68.00,
    ),
    ("1119806", "Pyramids of Giza Plateau: Skip the Line Ticket", 18.00),
    (
        "1122160",
        "Pyramids of Giza: Guided Tour + Quad or Camel Ride + Transfers",
        64.00,
    ),
    (
        "1121988",
        "Pyramids of Giza: Quad or Camel Ride + Transfers & Optional Entry Ticket",
        26.00,
    ),
    (
        "1128083",
        "Saladin Citadel & Mosque of Muhammad Ali: Skip The Line Ticket",
        14.00,
    ),
    ("1128180", "Saqqara Necropolis: Entry Ticket", 16.00),
]

SKIP_LINE = {
    "1115262",
    "1123804",
    "1132779",
    "1119806",
    "1128083",
    "1128180",
}
CRUISE = {"1116286", "1129181", "1129083"}
DINNER_TIMESLOT = {"1115096"}

HEADERS = [
    "Product ID",
    "Product Name",
    "Description",
    "Active",
    "Use Timeslots",
    "Is Refundable",
    "Provides Pricing",
    "Cutoff Time",
    "Max Tickets",
    "Required Order Data",
    "Required Visitor Data",
    "Adult Price",
    "Child Price",
    "Currency",
    "Daily Capacity",
    "Tickets Table Name",
    "Ticket View Name",
]

VISITOR = "full_name, email, phone"


def main() -> None:
    rows = []
    for pid, name, portal_start_price in PRODUCTS:
        is_skip = pid in SKIP_LINE
        use_timeslots = pid in CRUISE or pid in DINNER_TIMESLOT
        order_data = "" if is_skip else "pickup_location"
        tickets_table = "Grand_Tickets" if is_skip else ""
        ticket_view = "Tiqet" if is_skip else ""
        daily_cap = 200 if is_skip else 50
        desc = (
            f"Tiqets product {pid}. Portal starting price ${portal_start_price:.2f} "
            "(verify API Adult/Child vs supplier net)."
        )
        rows.append(
            {
                "Product ID": pid,
                "Product Name": name,
                "Description": desc,
                "Active": "true",
                "Use Timeslots": "true" if use_timeslots else "false",
                "Is Refundable": "true",
                "Provides Pricing": "true",
                "Cutoff Time": 24,
                "Max Tickets": 15,
                "Required Order Data": order_data,
                "Required Visitor Data": VISITOR,
                "Adult Price": portal_start_price,
                "Child Price": portal_start_price,
                "Currency": "USD",
                "Daily Capacity": daily_cap,
                "Tickets Table Name": tickets_table,
                "Ticket View Name": ticket_view,
            }
        )

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADERS, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
