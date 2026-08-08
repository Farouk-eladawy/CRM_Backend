import re
import json

with open('airtable_mirror.py', 'r', encoding='utf-8') as f:
    content = f.read()

batch_upsert = """    def _upsert_records_batch(self, table_key, records):
        if not records: return
        ts = _now_ts()
        values = []
        for rid, fields in records:
            try:
                fields_json = json.dumps(fields or {}, ensure_ascii=False)
            except Exception:
                fields_json = "{}"
            values.append((table_key, rid, fields_json, ts))
        with self._write_lock:
            with self._get_conn() as conn:
                c = conn.cursor()
                c.executemany(
                    \"\"\"
                    INSERT INTO mirror_records (table_key, airtable_id, fields_json, synced_ts)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(table_key, airtable_id) DO UPDATE SET
                        fields_json=excluded.fields_json,
                        synced_ts=excluded.synced_ts
                    \"\"\",
                    values,
                )

    def _update_list_projection_batch(self, records):
        if not records: return
        values = []
        fts_values = []
        for rid, fields in records:
            date_trip_raw = fields.get("Date Trip")
            date_trip_date = None
            try:
                if date_trip_raw:
                    d = _cairo_date(date_trip_raw, tz_offset_hours=3)
                    date_trip_date = d.isoformat() if d else None
            except Exception:
                pass
            pickup_time = fields.get("pickup time")
            booking_nr = fields.get("Booking Nr.")
            agency = fields.get("Agency")
            booking_status = fields.get("Booking Status")
            customer_phone = fields.get("Customer Phone")
            last_modified = fields.get("Last Modified")
            
            values.append((
                rid,
                str(date_trip_date) if date_trip_date else None,
                str(pickup_time) if pickup_time is not None else None,
                str(booking_nr) if booking_nr is not None else None,
                str(agency) if agency is not None else None,
                str(booking_status) if booking_status is not None else None,
                str(customer_phone) if customer_phone is not None else None,
                str(last_modified) if last_modified is not None else None,
            ))
            
            try:
                content_parts = []
                for k, v in (fields or {}).items():
                    if v is None: continue
                    if isinstance(v, (dict, list)):
                        s = json.dumps(v, ensure_ascii=False)
                    else:
                        s = str(v)
                    s = s.strip()
                    if not s: continue
                    content_parts.append(f"{k}: {s}")
                content = "\\n".join(content_parts)
                fts_values.append((rid, content))
            except Exception:
                pass
                
        with self._write_lock:
            with self._get_conn() as conn:
                c = conn.cursor()
                c.executemany(
                    \"\"\"
                    INSERT INTO mirror_list_projection (airtable_id, date_trip_date, pickup_time, booking_nr, agency, booking_status, customer_phone, last_modified_iso)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(airtable_id) DO UPDATE SET
                        date_trip_date=excluded.date_trip_date,
                        pickup_time=excluded.pickup_time,
                        booking_nr=excluded.booking_nr,
                        agency=excluded.agency,
                        booking_status=excluded.booking_status,
                        customer_phone=excluded.customer_phone,
                        last_modified_iso=excluded.last_modified_iso
                    \"\"\",
                    values,
                )
                try:
                    c.executemany("DELETE FROM mirror_list_fts WHERE airtable_id=?", [(r[0],) for r in fts_values])
                    c.executemany("INSERT INTO mirror_list_fts (airtable_id, content) VALUES (?, ?)", fts_values)
                except Exception:
                    pass"""

if 'def _upsert_records_batch' not in content:
    content = content.replace('    def upsert_main_list_record', batch_upsert + '\n\n    def upsert_main_list_record')

# Now modify sync_table to use batching
old_sync_code = """                    for rec in (page or []):
                        rid = rec.get("id")
                        keep_ids.add(rid)
                        fields = rec.get("fields", {}) or {}
                        self._upsert_record(table_key, rid, fields)
                        if info.get("base_label") == "main" and table_name == "List":
                            self._update_list_projection(rid, fields)
                        updated += 1
                        if has_lmt and lmt_field:
                            dt_val = _iso_to_dt(fields.get(lmt_field))
                            if dt_val and (newest_dt is None or dt_val > newest_dt):
                                newest_dt = dt_val"""

new_sync_code = """                    batch_records = []
                    for rec in (page or []):
                        rid = rec.get("id")
                        keep_ids.add(rid)
                        fields = rec.get("fields", {}) or {}
                        batch_records.append((rid, fields))
                        updated += 1
                        if has_lmt and lmt_field:
                            dt_val = _iso_to_dt(fields.get(lmt_field))
                            if dt_val and (newest_dt is None or dt_val > newest_dt):
                                newest_dt = dt_val
                    self._upsert_records_batch(table_key, batch_records)
                    if info.get("base_label") == "main" and table_name == "List":
                        self._update_list_projection_batch(batch_records)"""

content = content.replace(old_sync_code, new_sync_code)

old_sync_code_2 = """                    for rec in (page or []):
                        rid = rec.get("id")
                        fields = rec.get("fields", {}) or {}
                        ts_val = fields.get(lmt_field)
                        dt_val = _iso_to_dt(ts_val) or None
                        if stop_dt and dt_val and dt_val <= stop_dt:
                            stop = True
                            break
                        self._upsert_record(table_key, rid, fields)
                        if info.get("base_label") == "main" and table_name == "List":
                            self._update_list_projection(rid, fields)
                        updated += 1
                        if dt_val and (newest_dt is None or dt_val > newest_dt):
                            newest_dt = dt_val"""

new_sync_code_2 = """                    batch_records = []
                    for rec in (page or []):
                        rid = rec.get("id")
                        fields = rec.get("fields", {}) or {}
                        ts_val = fields.get(lmt_field)
                        dt_val = _iso_to_dt(ts_val) or None
                        if stop_dt and dt_val and dt_val <= stop_dt:
                            stop = True
                            break
                        batch_records.append((rid, fields))
                        updated += 1
                        if dt_val and (newest_dt is None or dt_val > newest_dt):
                            newest_dt = dt_val
                    self._upsert_records_batch(table_key, batch_records)
                    if info.get("base_label") == "main" and table_name == "List":
                        self._update_list_projection_batch(batch_records)"""

content = content.replace(old_sync_code_2, new_sync_code_2)

with open('airtable_mirror.py', 'w', encoding='utf-8') as f:
    f.write(content)
