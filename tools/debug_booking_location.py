import json
import sqlite3


def main():
    booking = "GYGVN29RY6FB"
    db = "airtable_mirror.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    row = c.execute(
        "select airtable_id, booking_nr, agency, booking_status, date_trip_date, pickup_time from mirror_list_projection where booking_nr=?",
        (booking,),
    ).fetchone()
    print("mirror_list_projection:", dict(row) if row else None)
    if not row:
        row = c.execute(
            "select airtable_id, booking_nr from mirror_list_projection where booking_nr like ?",
            (f"%{booking}%",),
        ).fetchone()
        print("fuzzy:", dict(row) if row else None)
        if not row:
            return

    air_id = row["airtable_id"]
    list_tables = c.execute(
        "select table_key, base_label, table_name from mirror_tables where table_name='List' and ignored=0"
    ).fetchall()
    print("List tables:", [dict(r) for r in list_tables])

    for t in list_tables:
        r = c.execute(
            "select fields_json from mirror_records where table_key=? and airtable_id=?",
            (t["table_key"], air_id),
        ).fetchone()
        if not r:
            continue
        fields = json.loads(r["fields_json"] or "{}")
        relevant = {
            k: fields.get(k)
            for k in fields.keys()
            if any(x in k.lower() for x in ("location", "city", "area", "region", "destination", "place"))
        }
        keys = list(relevant.keys())[:60]
        print("fields subset:", {k: relevant[k] for k in keys})
        for k in (
            "Location",
            "Area",
            "City",
            "Region",
            "Destination",
            "Pickup Location",
            "Hotel Name",
            "Trip Name",
        ):
            if k in fields:
                print(f"{k}:", fields.get(k))
        break


if __name__ == "__main__":
    main()
