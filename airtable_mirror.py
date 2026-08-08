import json
import logging
import os
from fts_paths import get_data_path, DATA_DIR
import re
import sqlite3
from contextlib import contextmanager
import threading
import time
import zlib
from datetime import datetime, timedelta, timezone

import requests
from pyairtable import Api
from urllib3.util.retry import Retry


def _now_ts():
    return int(time.time())


def _cairo_now(tz_offset_hours=3):
    try:
        import pytz

        return datetime.now(pytz.timezone("Africa/Cairo"))
    except Exception:
        dt_utc = datetime.now(timezone.utc)
        return dt_utc + timedelta(hours=int(tz_offset_hours or 0))


def _cairo_date(v, tz_offset_hours=3):
    if v is None:
        return None
    dt = None
    try:
        if isinstance(v, datetime):
            dt = v
        else:
            s = str(v).strip()
            if not s:
                return None
            if " " in s and "T" not in s:
                s = s.replace(" ", "T")
            if "T" not in s:
                return datetime.fromisoformat(s[:10]).date()
            dt = _iso_to_dt(s)
    except Exception:
        dt = None
    if not dt:
        try:
            s = str(v).strip()
            return datetime.fromisoformat(s[:10]).date() if s else None
        except Exception:
            return None
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        try:
            import pytz

            return dt.astimezone(pytz.timezone("Africa/Cairo")).date()
        except Exception:
            dt_utc = dt.astimezone(timezone.utc)
            return (dt_utc + timedelta(hours=int(tz_offset_hours or 0))).date()
    except Exception:
        return None


def _iso_to_dt(v):
    if not v:
        return None
    try:
        s = str(v).strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _dt_to_iso(dt):
    try:
        if not dt:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        return None


def _safe_table_key(base_id, table_id):
    return f"{base_id}:{table_id}"


class AirtableMirror:
    def __init__(self, config, db_path=None):
        self.config = config or {}
        self.db_path = db_path or get_data_path('airtable_mirror.db')
        self.base_id = (self.config.get("airtable", {}) or {}).get("base_id")
        self.religious_base_id = (self.config.get("airtable", {}) or {}).get("religious_base_id")
        self.trips_base_id = (self.config.get("airtable", {}) or {}).get("trips_base_id")
        self.api_key = (self.config.get("airtable", {}) or {}).get("api_key")
        self.ignored_table_names = {"Template"}
        self._full_sync_lock = threading.Lock()
        self._write_lock = threading.RLock()
        self._sqlite_init()
        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        self._api = Api(self.api_key, retry_strategy=retry_strategy, timeout=(5, 30))
        self._last_schema_refresh_ts = 0

    @contextmanager
    def _get_conn(self):
        conn = self._connect()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=60.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except Exception:
            pass
        try:
            conn.execute("PRAGMA synchronous=NORMAL")
        except Exception:
            pass
        try:
            conn.execute("PRAGMA busy_timeout=60000")
        except Exception:
            pass
        return conn

    def _sqlite_init(self):
        with self._write_lock:
            with self._get_conn() as conn:
                c = conn.cursor()
                c.execute(
                    """
                    CREATE TABLE IF NOT EXISTS mirror_tables (
                        table_key TEXT PRIMARY KEY,
                        base_id TEXT,
                        base_label TEXT,
                        table_id TEXT,
                        table_name TEXT,
                        ignored INTEGER DEFAULT 0,
                        has_lmt INTEGER DEFAULT 0,
                        lmt_field TEXT,
                        record_count INTEGER,
                        sync_interval_seconds INTEGER,
                        last_seen_ts INTEGER
                    )
                    """
                )
                c.execute(
                    """
                    CREATE TABLE IF NOT EXISTS mirror_fields (
                        table_key TEXT,
                        field_id TEXT,
                        field_name TEXT,
                        field_type TEXT,
                        PRIMARY KEY (table_key, field_id)
                    )
                    """
                )
                c.execute(
                    """
                    CREATE TABLE IF NOT EXISTS mirror_sync_state (
                        table_key TEXT PRIMARY KEY,
                        last_sync_iso TEXT,
                        last_full_sync_ts INTEGER,
                        next_sync_ts INTEGER
                    )
                    """
                )
                c.execute(
                    """
                    CREATE TABLE IF NOT EXISTS mirror_records (
                        table_key TEXT,
                        airtable_id TEXT,
                        fields_json TEXT,
                        synced_ts INTEGER,
                        PRIMARY KEY (table_key, airtable_id)
                    )
                    """
                )
                c.execute("CREATE INDEX IF NOT EXISTS idx_mirror_records_table ON mirror_records(table_key)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_mirror_records_synced ON mirror_records(table_key, synced_ts)")
                c.execute(
                    """
                    CREATE TABLE IF NOT EXISTS mirror_list_projection (
                        airtable_id TEXT PRIMARY KEY,
                        date_trip_date TEXT,
                        pickup_time TEXT,
                        booking_nr TEXT,
                        agency TEXT,
                        booking_status TEXT,
                        customer_phone TEXT,
                        last_modified_iso TEXT
                    )
                    """
                )
                c.execute("CREATE INDEX IF NOT EXISTS idx_list_proj_date ON mirror_list_projection(date_trip_date)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_list_proj_booking ON mirror_list_projection(booking_nr)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_list_proj_phone ON mirror_list_projection(customer_phone)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_list_proj_last_modified ON mirror_list_projection(last_modified_iso)")
                try:
                    c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS mirror_list_fts USING fts5(airtable_id UNINDEXED, content)")
                except Exception:
                    pass
                conn.commit()

    def _meta_tables(self, base_id):
        url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
        r = requests.get(url, headers={"Authorization": f"Bearer {self.api_key}"}, timeout=30)
        r.raise_for_status()
        return (r.json() or {}).get("tables", []) or []

    def refresh_schema(self, force=False):
        now = _now_ts()
        if not force and (now - int(self._last_schema_refresh_ts or 0) < 300):
            return
        self._last_schema_refresh_ts = now

        for base_label, base_id in (("main", self.base_id), ("religious", self.religious_base_id), ("trips", self.trips_base_id)):
            if not base_id:
                continue
            try:
                tables = self._meta_tables(base_id)
            except Exception as e:
                logging.error(f"Mirror schema refresh failed for base {base_label}: {e}")
                continue
            with self._write_lock:
                with self._get_conn() as conn:
                    c = conn.cursor()
                    for t in (tables or []):
                        t_name = str(t.get("name") or "").strip()
                        t_id = str(t.get("id") or "").strip()
                        if not t_id or not t_name:
                            continue
                        table_key = _safe_table_key(base_id, t_id)
                        ignored = 1 if t_name in self.ignored_table_names else 0
                        fields = t.get("fields", []) or []
                        lmt_fields = [f.get("name") for f in fields if f.get("type") == "lastModifiedTime" and f.get("name")]
                        has_lmt = 1 if len(lmt_fields) > 0 else 0
                        preferred_lmt = None
                        if has_lmt:
                            if "Last Modified" in lmt_fields:
                                preferred_lmt = "Last Modified"
                            else:
                                preferred_lmt = str(lmt_fields[0])
                        c.execute(
                            """
                            INSERT INTO mirror_tables (table_key, base_id, base_label, table_id, table_name, ignored, has_lmt, lmt_field, last_seen_ts)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(table_key) DO UPDATE SET
                                base_label=excluded.base_label,
                                table_name=excluded.table_name,
                                ignored=excluded.ignored,
                                has_lmt=excluded.has_lmt,
                                lmt_field=excluded.lmt_field,
                                last_seen_ts=excluded.last_seen_ts
                            """,
                            (table_key, base_id, base_label, t_id, t_name, ignored, has_lmt, preferred_lmt, now),
                        )
                        for f in (fields or []):
                            f_id = str(f.get("id") or "").strip()
                            f_name = str(f.get("name") or "").strip()
                            f_type = str(f.get("type") or "").strip()
                            if not f_id or not f_name:
                                continue
                            c.execute(
                                """
                                INSERT INTO mirror_fields (table_key, field_id, field_name, field_type)
                                VALUES (?, ?, ?, ?)
                                ON CONFLICT(table_key, field_id) DO UPDATE SET
                                    field_name=excluded.field_name,
                                    field_type=excluded.field_type
                                """,
                                (table_key, f_id, f_name, f_type),
                            )
                    conn.commit()

        self._ensure_intervals()

    def _estimate_record_count(self, base_id, table_name, cap=1601):
        try:
            tbl = self._api.table(base_id, table_name)
            cnt = 0
            for page in tbl.iterate(page_size=50, max_records=cap):
                cnt += len(page)
                if cnt >= cap:
                    break
            return cnt if cnt < cap else cap
        except Exception:
            return None

    def _interval_from_count(self, n):
        if n is None:
            return 900
        if n <= 200:
            return 60
        if n <= 800:
            return 300
        if n <= 1500:
            return 600
        return 900

    def _ensure_intervals(self):
        with self._write_lock:
            with self._get_conn() as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM mirror_tables")
                rows = c.fetchall() or []
                for r in rows:
                    ignored = int(r["ignored"] or 0) == 1
                    if ignored:
                        interval = None
                    else:
                        has_lmt = int(r["has_lmt"] or 0) == 1
                        if has_lmt:
                            interval = 60
                        else:
                            rc = r["record_count"]
                            interval = self._interval_from_count(rc)
                    c.execute(
                        "UPDATE mirror_tables SET sync_interval_seconds=? WHERE table_key=?",
                        (interval, r["table_key"]),
                    )
                conn.commit()

    def _get_table_key_for_main_list(self, is_religious=False, table_name=None):
        with self._get_conn() as conn:
            c = conn.cursor()
            if is_religious:
                target_name = str(table_name or "").strip()
                if target_name:
                    c.execute(
                        "SELECT table_key FROM mirror_tables WHERE base_label='religious' AND table_name=? LIMIT 1",
                        (target_name,),
                    )
                else:
                    c.execute(
                        """
                        SELECT table_key
                        FROM mirror_tables
                        WHERE base_label='religious' AND ignored=0
                        ORDER BY CASE WHEN table_name='استفسارات جديدة' THEN 0 ELSE 1 END, table_name ASC
                        LIMIT 1
                        """
                    )
            else:
                c.execute(
                    "SELECT table_key FROM mirror_tables WHERE base_label='main' AND table_name='List' LIMIT 1"
                )
            row = c.fetchone()
            return row["table_key"] if row else None

    def _list_table_info(self):
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM mirror_tables WHERE ignored=0")
            return [dict(r) for r in (c.fetchall() or [])]

    def _ensure_record_count(self, info):
        try:
            if info.get("has_lmt"):
                return
            if info.get("record_count") is not None:
                return
            base_id = info.get("base_id")
            table_name = info.get("table_name")
            if not base_id or not table_name:
                return
            cnt = self._estimate_record_count(base_id, table_name)
            with self._write_lock:
                with self._get_conn() as conn:
                    c = conn.cursor()
                    c.execute(
                        "UPDATE mirror_tables SET record_count=? WHERE table_key=?",
                        (cnt, info.get("table_key")),
                    )
                    conn.commit()
            info["record_count"] = cnt
        except Exception:
            return

    def _upsert_record(self, table_key, rec_id, fields):
        try:
            fields_json = json.dumps(fields or {}, ensure_ascii=False)
        except Exception:
            fields_json = "{}"
        ts = _now_ts()
        with self._write_lock:
            with self._get_conn() as conn:
                c = conn.cursor()
                c.execute(
                    """
                    INSERT INTO mirror_records (table_key, airtable_id, fields_json, synced_ts)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(table_key, airtable_id) DO UPDATE SET
                        fields_json=excluded.fields_json,
                        synced_ts=excluded.synced_ts
                    """,
                    (table_key, rec_id, fields_json, ts),
                )
                conn.commit()

    def _delete_missing(self, table_key, keep_ids, cleanup_main_list=False):
        keep_ids = set(keep_ids or [])
        with self._write_lock:
            with self._get_conn() as conn:
                c = conn.cursor()
                if not keep_ids:
                    c.execute("DELETE FROM mirror_records WHERE table_key=?", (table_key,))
                    if cleanup_main_list:
                        c.execute("DELETE FROM mirror_list_projection")
                        try:
                            c.execute("DELETE FROM mirror_list_fts")
                        except Exception:
                            pass
                    conn.commit()
                    return

                if len(keep_ids) <= 900:
                    placeholders = ",".join(["?"] * len(keep_ids))
                    c.execute(
                        f"DELETE FROM mirror_records WHERE table_key=? AND airtable_id NOT IN ({placeholders})",
                        [table_key] + list(keep_ids),
                    )
                    if cleanup_main_list:
                        c.execute(
                            f"DELETE FROM mirror_list_projection WHERE airtable_id NOT IN ({placeholders})",
                            list(keep_ids),
                        )
                        try:
                            c.execute(
                                f"DELETE FROM mirror_list_fts WHERE airtable_id NOT IN ({placeholders})",
                                list(keep_ids),
                            )
                        except Exception:
                            pass
                    conn.commit()
                    return

                c.execute("CREATE TEMP TABLE IF NOT EXISTS tmp_keep_ids (airtable_id TEXT PRIMARY KEY)")
                c.execute("DELETE FROM tmp_keep_ids")
                c.executemany("INSERT OR IGNORE INTO tmp_keep_ids (airtable_id) VALUES (?)", [(x,) for x in keep_ids])
                c.execute(
                    "DELETE FROM mirror_records WHERE table_key=? AND airtable_id NOT IN (SELECT airtable_id FROM tmp_keep_ids)",
                    (table_key,),
                )
                if cleanup_main_list:
                    c.execute("DELETE FROM mirror_list_projection WHERE airtable_id NOT IN (SELECT airtable_id FROM tmp_keep_ids)")
                    try:
                        c.execute("DELETE FROM mirror_list_fts WHERE airtable_id NOT IN (SELECT airtable_id FROM tmp_keep_ids)")
                    except Exception:
                        pass
                conn.commit()

    def _update_list_projection(self, airtable_id, fields):
        date_trip_raw = fields.get("Date Trip")
        date_trip_date = None
        try:
            if date_trip_raw:
                d = _cairo_date(date_trip_raw, tz_offset_hours=3)
                date_trip_date = d.isoformat() if d else None
        except Exception:
            date_trip_date = None
        pickup_time = fields.get("pickup time")
        booking_nr = fields.get("Booking Nr.")
        agency = fields.get("Agency")
        booking_status = fields.get("Booking Status")
        customer_phone = fields.get("Customer Phone")
        last_modified = fields.get("Last Modified")
        with self._write_lock:
            with self._get_conn() as conn:
                c = conn.cursor()
                c.execute(
                    """
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
                    """,
                    (
                        airtable_id,
                        str(date_trip_date) if date_trip_date else None,
                        str(pickup_time) if pickup_time is not None else None,
                        str(booking_nr) if booking_nr is not None else None,
                        str(agency) if agency is not None else None,
                        str(booking_status) if booking_status is not None else None,
                        str(customer_phone) if customer_phone is not None else None,
                        str(last_modified) if last_modified is not None else None,
                    ),
                )
                try:
                    content_parts = []
                    for k, v in (fields or {}).items():
                        if v is None:
                            continue
                        if isinstance(v, (dict, list)):
                            s = json.dumps(v, ensure_ascii=False)
                        else:
                            s = str(v)
                        s = s.strip()
                        if not s:
                            continue
                        content_parts.append(f"{k}: {s}")
                    content = "\n".join(content_parts)
                    c.execute("DELETE FROM mirror_list_fts WHERE airtable_id=?", (airtable_id,))
                    c.execute("INSERT INTO mirror_list_fts (airtable_id, content) VALUES (?, ?)", (airtable_id, content))
                except Exception:
                    pass
                conn.commit()

    def _upsert_records_batch(self, table_key, records):
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
                    """
                    INSERT INTO mirror_records (table_key, airtable_id, fields_json, synced_ts)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(table_key, airtable_id) DO UPDATE SET
                        fields_json=excluded.fields_json,
                        synced_ts=excluded.synced_ts
                    """,
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
                content = "\n".join(content_parts)
                fts_values.append((rid, content))
            except Exception:
                pass
                
        with self._write_lock:
            with self._get_conn() as conn:
                c = conn.cursor()
                c.executemany(
                    """
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
                    """,
                    values,
                )
                try:
                    c.executemany("DELETE FROM mirror_list_fts WHERE airtable_id=?", [(r[0],) for r in fts_values])
                    c.executemany("INSERT INTO mirror_list_fts (airtable_id, content) VALUES (?, ?)", fts_values)
                except Exception:
                    pass

    def upsert_main_list_record(self, airtable_id, fields, override_table_key=None):
        table_key = str(override_table_key or "").strip() or None
        if not table_key:
            try:
                table_key = self._get_table_key_for_main_list()
            except Exception:
                table_key = None
        if not table_key or not airtable_id:
            return False
        try:
            self._upsert_record(table_key, str(airtable_id), fields or {})
            try:
                if table_key == self._get_table_key_for_main_list():
                    self._update_list_projection(str(airtable_id), fields or {})
            except Exception:
                pass
            return True
        except Exception:
            return False

    def _set_sync_state(self, table_key, last_sync_iso=None, last_full_sync_ts=None, next_sync_ts=None):
        with self._write_lock:
            with self._get_conn() as conn:
                c = conn.cursor()
                c.execute(
                    """
                    INSERT INTO mirror_sync_state (table_key, last_sync_iso, last_full_sync_ts, next_sync_ts)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(table_key) DO UPDATE SET
                        last_sync_iso=COALESCE(excluded.last_sync_iso, mirror_sync_state.last_sync_iso),
                        last_full_sync_ts=COALESCE(excluded.last_full_sync_ts, mirror_sync_state.last_full_sync_ts),
                        next_sync_ts=COALESCE(excluded.next_sync_ts, mirror_sync_state.next_sync_ts)
                    """,
                    (table_key, last_sync_iso, last_full_sync_ts, next_sync_ts),
                )
                conn.commit()

    def _get_sync_state(self, table_key):
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM mirror_sync_state WHERE table_key=?", (table_key,))
            row = c.fetchone()
            return dict(row) if row else {}

    def _should_run_scheduled_full_sync(self, table_key, state, interval_hours=6, tz_offset_hours=3, jitter_max_minutes=15):
        try:
            now_local = _cairo_now(tz_offset_hours=tz_offset_hours)
            if now_local.tzinfo is None:
                now_local = now_local.replace(tzinfo=timezone.utc)
            now_utc = now_local.astimezone(timezone.utc)
            now_ts = int(now_utc.timestamp())

            h = int(now_local.hour or 0)
            window_hour = (h // int(interval_hours or 6)) * int(interval_hours or 6)
            window_start_local = now_local.replace(hour=window_hour, minute=0, second=0, microsecond=0)
            window_start_utc = window_start_local.astimezone(timezone.utc)
            window_start_ts = int(window_start_utc.timestamp())
            window_end_ts = window_start_ts + int(interval_hours or 6) * 3600

            last_full = state.get("last_full_sync_ts")
            try:
                last_full = int(last_full) if last_full is not None else None
            except Exception:
                last_full = None
            if last_full is not None and window_start_ts <= last_full < window_end_ts:
                return False

            sig = f"{table_key}:{window_start_ts}".encode("utf-8")
            jitter = int(abs(zlib.crc32(sig)) % (int(jitter_max_minutes or 15) + 1))
            if now_ts < window_start_ts + jitter * 60:
                return False
            return True
        except Exception:
            return False

    def sync_table(self, info, force_full=False):
        table_key = info.get("table_key")
        base_id = info.get("base_id")
        table_name = info.get("table_name")
        if not table_key or not base_id or not table_name:
            return
        if int(info.get("ignored") or 0) == 1:
            return
        self._ensure_record_count(info)
        has_lmt = int(info.get("has_lmt") or 0) == 1
        interval = info.get("sync_interval_seconds")
        if (not has_lmt) and info.get("record_count") is not None:
            try:
                interval = self._interval_from_count(int(info.get("record_count") or 0))
            except Exception:
                interval = self._interval_from_count(None)
            info["sync_interval_seconds"] = interval
            try:
                with self._write_lock:
                    with self._get_conn() as conn:
                        c = conn.cursor()
                        c.execute("UPDATE mirror_tables SET sync_interval_seconds=? WHERE table_key=?", (interval, table_key))
                        conn.commit()
            except Exception:
                pass
        if interval is None:
            return
        state = self._get_sync_state(table_key)
        is_main_list = info.get("base_label") == "main" and table_name == "List"
        if is_main_list and not force_full:
            if self._should_run_scheduled_full_sync(table_key, state, interval_hours=6, tz_offset_hours=3, jitter_max_minutes=15):
                force_full = True

        next_sync_ts = state.get("next_sync_ts")
        if not force_full and next_sync_ts and _now_ts() < int(next_sync_ts):
            return

        lmt_field = info.get("lmt_field")
        tbl = self._api.table(base_id, table_name)

        if has_lmt and lmt_field and not force_full:
            last_sync_iso = state.get("last_sync_iso")
            last_dt = _iso_to_dt(last_sync_iso)
            stop_dt = last_dt
            newest_dt = last_dt
            updated = 0
            stop = False
            try:
                for page in tbl.iterate(page_size=50):
                    if stop:
                        break
                    batch_records = []
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
                        self._update_list_projection_batch(batch_records)
                if updated > 0 and newest_dt:
                    self._set_sync_state(table_key, last_sync_iso=_dt_to_iso(newest_dt))
            except Exception as e:
                logging.error(f"Mirror delta sync failed for {table_name}: {e}")
        else:
            lock_acquired = False
            if is_main_list:
                lock_acquired = self._full_sync_lock.acquire(blocking=False)
                if not lock_acquired:
                    return
            keep_ids = set()
            newest_dt = None
            updated = 0
            try:
                if is_main_list:
                    logging.info("Mirror full sync started for main List (scheduled)")
                for page in tbl.iterate(page_size=50):
                    batch_records = []
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
                        self._update_list_projection_batch(batch_records)
                self._delete_missing(table_key, keep_ids, cleanup_main_list=is_main_list)
                now_ts = _now_ts()
                self._set_sync_state(table_key, last_full_sync_ts=now_ts)
                if newest_dt:
                    self._set_sync_state(table_key, last_sync_iso=_dt_to_iso(newest_dt))
            except Exception as e:
                logging.error(f"Mirror full sync failed for {table_name}: {e}")
            finally:
                if lock_acquired:
                    self._full_sync_lock.release()

        next_ts = _now_ts() + int(interval or 60)
        self._set_sync_state(table_key, next_sync_ts=next_ts)

    def tick(self):
        self.refresh_schema()
        tables = self._list_table_info()
        for info in tables:
            try:
                self.sync_table(info)
            except Exception:
                continue

    def status(self):
        out = []
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT t.base_label, t.table_name, t.ignored, t.has_lmt, t.lmt_field, t.record_count, t.sync_interval_seconds,
                       s.last_sync_iso, s.last_full_sync_ts, s.next_sync_ts
                FROM mirror_tables t
                LEFT JOIN mirror_sync_state s ON s.table_key = t.table_key
                ORDER BY t.base_label, t.table_name
                """
            )
            for r in (c.fetchall() or []):
                out.append(dict(r))
        return out

    def list_schema_for_main_list(self, is_religious=False, table_name=None):
        with self._get_conn() as conn:
            c = conn.cursor()
            if is_religious:
                target_name = str(table_name or "").strip()
                if target_name:
                    c.execute(
                        """
                        SELECT mf.field_name, mf.field_type
                        FROM mirror_fields mf
                        JOIN mirror_tables mt ON mt.table_key = mf.table_key
                        WHERE mt.base_label='religious' AND mt.table_name=?
                        ORDER BY mf.field_name
                        """,
                        (target_name,),
                    )
                    return [dict(r) for r in (c.fetchall() or [])]

                c.execute(
                    """
                    SELECT mf.field_name, MIN(mf.field_type) AS field_type
                    FROM mirror_fields mf
                    JOIN mirror_tables mt ON mt.table_key = mf.table_key
                    WHERE mt.base_label='religious' AND mt.ignored=0
                    GROUP BY mf.field_name
                    ORDER BY mf.field_name
                    """
                )
                return [dict(r) for r in (c.fetchall() or [])]

            table_key = self._get_table_key_for_main_list()
            if not table_key:
                return []
            c.execute(
                "SELECT field_name, field_type FROM mirror_fields WHERE table_key=? ORDER BY field_name",
                (table_key,),
            )
            return [dict(r) for r in (c.fetchall() or [])]

    def is_main_list_ready(self, min_rows=1):
        try:
            with self._get_conn() as conn:
                c = conn.cursor()
                c.execute("SELECT COUNT(1) AS n FROM mirror_list_projection")
                row = c.fetchone()
                n = int((row["n"] if row else 0) or 0)
                return n >= int(min_rows or 1)
        except Exception:
            return False

    def query_operations_view(self, view_name, offset=0, limit=100, tz_offset_hours=3):
        table_key = self._get_table_key_for_main_list()
        if not table_key:
            return [], None
        now = _cairo_now(tz_offset_hours=tz_offset_hours)
        today = now.date()
        start = None
        end = None

        v = str(view_name or "").strip()
        if v in ("Operation Today", "Booking_today"):
            start = today
            end = today
        elif v in ("Operation Tomorrow", "Booking_tomorrow"):
            start = today + timedelta(days=1)
            end = start
        elif v in ("Operation Weekly", "Booking_Weekly"):
            start = today
            end = today + timedelta(days=7)
        elif v in ("All Booking", "All Bookings"):
            start = None
            end = None
        else:
            return [], None

        o = max(0, int(offset or 0))
        l = max(1, min(1000, int(limit or 100)))
        if start is None:
            with self._get_conn() as conn:
                c = conn.cursor()
                c.execute(
                    """
                    SELECT p.airtable_id
                    FROM mirror_list_projection p
                    ORDER BY COALESCE(p.last_modified_iso, '') DESC, COALESCE(p.date_trip_date, '') DESC, COALESCE(p.booking_nr, '') ASC
                    LIMIT ? OFFSET ?
                    """,
                    (l + 1, o),
                )
                ids = [r["airtable_id"] for r in (c.fetchall() or [])]
            has_more = len(ids) > l
            ids = ids[:l]
            if not ids:
                return [], None
            placeholders = ",".join(["?"] * len(ids))
            with self._get_conn() as conn:
                c = conn.cursor()
                c.execute(
                    f"SELECT airtable_id, fields_json FROM mirror_records WHERE table_key=? AND airtable_id IN ({placeholders})",
                    [table_key] + ids,
                )
                by_id = {}
                for r in (c.fetchall() or []):
                    try:
                        by_id[r["airtable_id"]] = json.loads(r["fields_json"] or "{}")
                    except Exception:
                        by_id[r["airtable_id"]] = {}
            out = [{"id": rid, "fields": by_id.get(rid, {})} for rid in ids]
            next_offset = str(o + l) if has_more else None
            return out, next_offset

        start_s = (start - timedelta(days=1)).isoformat()
        end_s = (end + timedelta(days=1)).isoformat()
        want_n = o + l + 1
        matched = []
        scan_offset = 0
        batch_size = 2500
        while len(matched) < want_n:
            with self._get_conn() as conn:
                c = conn.cursor()
                c.execute(
                    """
                    SELECT p.airtable_id
                    FROM mirror_list_projection p
                    WHERE p.date_trip_date IS NOT NULL AND p.date_trip_date >= ? AND p.date_trip_date <= ?
                    ORDER BY p.date_trip_date ASC, COALESCE(p.pickup_time, '') ASC, COALESCE(p.booking_nr, '') ASC
                    LIMIT ? OFFSET ?
                    """,
                    (start_s, end_s, batch_size, scan_offset),
                )
                ids = [r["airtable_id"] for r in (c.fetchall() or [])]
            if not ids:
                break
            scan_offset += len(ids)
            placeholders = ",".join(["?"] * len(ids))
            with self._get_conn() as conn:
                c = conn.cursor()
                c.execute(
                    f"SELECT airtable_id, fields_json FROM mirror_records WHERE table_key=? AND airtable_id IN ({placeholders})",
                    [table_key] + list(ids),
                )
                for rid, fj in (c.fetchall() or []):
                    try:
                        fields = json.loads(fj or "{}")
                    except Exception:
                        fields = {}
                    d = _cairo_date((fields or {}).get("Date Trip"), tz_offset_hours=tz_offset_hours)
                    if not d:
                        continue
                    if d < start or d > end:
                        continue
                    matched.append({"id": rid, "fields": fields})

        if not matched:
            return [], None
        matched.sort(
            key=lambda r: (
                (_cairo_date((r.get("fields") or {}).get("Date Trip"), tz_offset_hours=tz_offset_hours) or datetime.max.date()).isoformat(),
                str((r.get("fields") or {}).get("pickup time") or ""),
                str((r.get("fields") or {}).get("Booking Nr.") or ""),
            )
        )
        page = matched[o : o + l]
        has_more = len(matched) > (o + l)
        next_offset = str(o + l) if has_more else None
        return page, next_offset

    def query_operations_view_advanced(self, view_name, offset=0, limit=100, tz_offset_hours=3, search=None, filters=None, sorts=None, is_religious=False):
        table_key = self._get_table_key_for_main_list()
        if not table_key:
            return [], None

        now = _cairo_now(tz_offset_hours=tz_offset_hours)
        today = now.date()
        start = None
        end = None

        v = str(view_name or "").strip()
        if v in ("Operation Today", "Booking_today"):
            start = today
            end = today
        elif v in ("Operation Tomorrow", "Booking_tomorrow"):
            start = today + timedelta(days=1)
            end = start
        elif v in ("Operation Weekly", "Booking_Weekly"):
            start = today
            end = today + timedelta(days=7)
        elif v in ("All Booking", "All Bookings"):
            start = None
            end = None
        else:
            return [], None

        o = max(0, int(offset or 0))
        l = max(1, min(1000, int(limit or 100)))

        q = str(search or "").strip()
        fs = filters if isinstance(filters, list) else []
        ss = sorts if isinstance(sorts, list) else []
        if not q and not fs and not ss:
            return self.query_operations_view(view_name=view_name, offset=o, limit=l, tz_offset_hours=tz_offset_hours)

        fts_ids = None
        if q:
            tokens = re.findall(r"[A-Za-z0-9]+", q.lower())
            tokens = [t for t in tokens if len(t) >= 2]
            if tokens:
                fts_query = " AND ".join([f"{t}*" for t in tokens])
                try:
                    with self._get_conn() as conn:
                        c = conn.cursor()
                        c.execute("SELECT airtable_id FROM mirror_list_fts WHERE mirror_list_fts MATCH ? LIMIT 50000", (fts_query,))
                        fts_ids = set([r[0] for r in (c.fetchall() or [])])
                except Exception:
                    fts_ids = None

        schema_types = {}
        try:
            for it in self.list_schema_for_main_list() or []:
                name = str(it.get("field_name") or "").strip()
                typ = str(it.get("field_type") or "").strip().lower()
                if not name:
                    continue
                if "date" in typ or "time" in typ or typ in ("createdtime", "lastmodifiedtime"):
                    schema_types[name] = "date"
                elif "select" in typ or "checkbox" in typ:
                    schema_types[name] = "select"
                else:
                    schema_types[name] = "text"
        except Exception:
            schema_types = {}

        def _to_lower_str(v):
            if v is None:
                return ""
            if isinstance(v, list):
                try:
                    return " ".join([str(x) for x in v]).lower()
                except Exception:
                    return str(v).lower()
            if isinstance(v, dict):
                try:
                    return json.dumps(v, ensure_ascii=False).lower()
                except Exception:
                    return str(v).lower()
            return str(v).lower()

        def _parse_date(v):
            if v is None:
                return None
            try:
                s = str(v).strip()
                if not s:
                    return None
                if "T" in s:
                    dt = _iso_to_dt(s)
                    if not dt:
                        return None
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    try:
                        import pytz

                        return dt.astimezone(pytz.timezone("Africa/Cairo")).date()
                    except Exception:
                        dt_utc = dt.astimezone(timezone.utc)
                        return (dt_utc + timedelta(hours=int(tz_offset_hours or 0))).date()
                return datetime.fromisoformat(s.split(" ", 1)[0]).date()
            except Exception:
                try:
                    return datetime.fromisoformat(str(v)).date()
                except Exception:
                    return None

        def _eval_node(fields, cond):
            if not cond:
                return True
            if cond.get("isGroup") and isinstance(cond.get("conditions"), list):
                kids = cond.get("conditions") or []
                if not kids:
                    return True
                logic = str(cond.get("groupLogic") or "and").lower()
                out = _eval_node(fields, kids[0])
                for i in range(1, len(kids)):
                    child = _eval_node(fields, kids[i])
                    if logic == "and":
                        out = out and child
                    else:
                        out = out or child
                return out

            field = cond.get("field")
            op = cond.get("operator")
            if not field or not op:
                return True
            val_raw = (fields or {}).get(field)
            val = _to_lower_str(val_raw)
            cond_val = _to_lower_str(cond.get("value"))
            ftype = schema_types.get(field) or "text"

            if ftype == "date" and val and op in ("is today", "is tomorrow", "is yesterday"):
                d_field = _parse_date(val_raw)
                if not d_field:
                    return False
                target = today
                if op == "is tomorrow":
                    target = today + timedelta(days=1)
                elif op == "is yesterday":
                    target = today - timedelta(days=1)
                return d_field == target

            if op == "contains":
                return cond_val in val
            if op == "does not contain":
                return cond_val not in val
            if op == "is":
                if ftype == "date" and val_raw is not None and cond.get("value"):
                    d1 = _parse_date(val_raw)
                    d2 = _parse_date(cond.get("value"))
                    if d1 and d2:
                        return d1 == d2
                if isinstance(val_raw, list):
                    return any(_to_lower_str(x) == cond_val for x in val_raw)
                return val == cond_val
            if op == "is not":
                if isinstance(val_raw, list):
                    return all(_to_lower_str(x) != cond_val for x in val_raw)
                return val != cond_val
            if op == "is empty":
                return val == ""
            if op == "is not empty":
                return val != ""
            if op == "is before":
                d1 = _parse_date(val_raw)
                d2 = _parse_date(cond.get("value"))
                return bool(d1 and d2 and d1 < d2)
            if op == "is after":
                d1 = _parse_date(val_raw)
                d2 = _parse_date(cond.get("value"))
                return bool(d1 and d2 and d1 > d2)
            return True

        def _matches_filters(fields):
            if not fs:
                return True
            is_match = _eval_node(fields, fs[0])
            for i in range(1, len(fs)):
                cm = _eval_node(fields, fs[i])
                if str((fs[i] or {}).get("connector") or "and").lower() == "and":
                    is_match = is_match and cm
                else:
                    is_match = is_match or cm
            return is_match
        batch_size = 2500
        scan_offset = 0
        max_scan = 60000
        records = []
        scanned = 0
        scan_target = o + l + 500
        if ss:
            scan_target = max(scan_target, 8000)

        def _fetch_projection_ids(limit_n, offset_n):
            with self._get_conn() as conn:
                c = conn.cursor()
                if start is None:
                    c.execute(
                        """
                        SELECT p.airtable_id
                        FROM mirror_list_projection p
                        ORDER BY COALESCE(p.last_modified_iso, '') DESC, COALESCE(p.date_trip_date, '') DESC, COALESCE(p.booking_nr, '') ASC
                        LIMIT ? OFFSET ?
                        """,
                        (limit_n, offset_n),
                    )
                else:
                    start_s = (start - timedelta(days=1)).isoformat()
                    end_s = (end + timedelta(days=1)).isoformat()
                    c.execute(
                        """
                        SELECT p.airtable_id
                        FROM mirror_list_projection p
                        WHERE p.date_trip_date IS NOT NULL AND p.date_trip_date >= ? AND p.date_trip_date <= ?
                        ORDER BY p.date_trip_date ASC, COALESCE(p.pickup_time, '') ASC, COALESCE(p.booking_nr, '') ASC
                        LIMIT ? OFFSET ?
                        """,
                        (start_s, end_s, limit_n, offset_n),
                    )
                return [r[0] for r in (c.fetchall() or [])]

        def _fetch_records_by_ids(ids):
            if not ids:
                return []
            placeholders = ",".join(["?"] * len(ids))
            with self._get_conn() as conn:
                c = conn.cursor()
                c.execute(
                    f"SELECT airtable_id, fields_json FROM mirror_records WHERE table_key=? AND airtable_id IN ({placeholders})",
                    [table_key] + list(ids),
                )
                out = []
                for rid, fj in (c.fetchall() or []):
                    try:
                        fields = json.loads(fj or "{}")
                    except Exception:
                        fields = {}
                    out.append({"id": rid, "fields": fields})
                return out

        filters_applied_in_scan = True
        while scanned < max_scan and len(records) < scan_target:
            ids = _fetch_projection_ids(batch_size, scan_offset)
            if not ids:
                break
            scan_offset += len(ids)
            scanned += len(ids)
            if fts_ids is not None:
                ids = [rid for rid in ids if rid in fts_ids]
                if not ids:
                    continue
            batch_records = _fetch_records_by_ids(ids)
            if batch_records:
                for r in batch_records:
                    f = r.get("fields") or {}
                    if start is not None:
                        d = _cairo_date(f.get("Date Trip"), tz_offset_hours=tz_offset_hours)
                        if not d or d < start or d > end:
                            continue
                    if fs and not _matches_filters(f):
                        continue
                    records.append(r)

        schema_types = {}
        try:
            for it in self.list_schema_for_main_list() or []:
                name = str(it.get("field_name") or "").strip()
                typ = str(it.get("field_type") or "").strip().lower()
                if not name:
                    continue
                if "date" in typ or "time" in typ or typ in ("createdtime", "lastmodifiedtime"):
                    schema_types[name] = "date"
                elif "select" in typ or "checkbox" in typ:
                    schema_types[name] = "select"
                else:
                    schema_types[name] = "text"
        except Exception:
            schema_types = {}

        def _get_val(fields, field):
            try:
                return fields.get(field)
            except Exception:
                return None

        def _to_lower_str(v):
            if v is None:
                return ""
            if isinstance(v, list):
                try:
                    return " ".join([str(x) for x in v]).lower()
                except Exception:
                    return str(v).lower()
            if isinstance(v, dict):
                try:
                    return json.dumps(v, ensure_ascii=False).lower()
                except Exception:
                    return str(v).lower()
            return str(v).lower()

        def _parse_date(v):
            if v is None:
                return None
            try:
                s = str(v).strip()
                if not s:
                    return None
                if "T" in s:
                    dt = _iso_to_dt(s)
                    return dt.date() if dt else None
                return datetime.fromisoformat(s.split(" ", 1)[0]).date()
            except Exception:
                try:
                    return datetime.fromisoformat(str(v)).date()
                except Exception:
                    return None

        def _eval_node(fields, cond):
            if not cond:
                return True
            if cond.get("isGroup") and isinstance(cond.get("conditions"), list):
                kids = cond.get("conditions") or []
                if not kids:
                    return True
                logic = str(cond.get("groupLogic") or "and").lower()
                out = _eval_node(fields, kids[0])
                for i in range(1, len(kids)):
                    child = _eval_node(fields, kids[i])
                    if logic == "and":
                        out = out and child
                    else:
                        out = out or child
                return out

            field = cond.get("field")
            op = cond.get("operator")
            if not field or not op:
                return True
            val_raw = _get_val(fields, field)
            val = _to_lower_str(val_raw)
            cond_val = _to_lower_str(cond.get("value"))
            ftype = schema_types.get(field) or "text"

            if ftype == "date" and val and op in ("is today", "is tomorrow", "is yesterday"):
                d_field = _parse_date(val_raw)
                if not d_field:
                    return False
                target = today
                if op == "is tomorrow":
                    target = today + timedelta(days=1)
                elif op == "is yesterday":
                    target = today - timedelta(days=1)
                return d_field == target

            if op == "contains":
                return cond_val in val
            if op == "does not contain":
                return cond_val not in val
            if op == "is":
                if ftype == "date" and val_raw is not None and cond.get("value"):
                    d1 = _parse_date(val_raw)
                    d2 = _parse_date(cond.get("value"))
                    if d1 and d2:
                        return d1 == d2
                if isinstance(val_raw, list):
                    return any(_to_lower_str(x) == cond_val for x in val_raw)
                return val == cond_val
            if op == "is not":
                if isinstance(val_raw, list):
                    return all(_to_lower_str(x) != cond_val for x in val_raw)
                return val != cond_val
            if op == "is empty":
                return val == ""
            if op == "is not empty":
                return val != ""
            if op == "is before":
                d1 = _parse_date(val_raw)
                d2 = _parse_date(cond.get("value"))
                return bool(d1 and d2 and d1 < d2)
            if op == "is after":
                d1 = _parse_date(val_raw)
                d2 = _parse_date(cond.get("value"))
                return bool(d1 and d2 and d1 > d2)
            return True

        if fs and not filters_applied_in_scan:
            next_records = []
            for r in records:
                f = r.get("fields") or {}
                is_match = _eval_node(f, fs[0])
                for i in range(1, len(fs)):
                    cm = _eval_node(f, fs[i])
                    if str((fs[i] or {}).get("connector") or "and").lower() == "and":
                        is_match = is_match and cm
                    else:
                        is_match = is_match or cm
                if is_match:
                    next_records.append(r)
            records = next_records

        if ss:
            for s in reversed(ss):
                field = str(s.get("field") or "").strip()
                direction = str(s.get("direction") or "asc").lower()
                if not field:
                    continue
                ftype = schema_types.get(field) or "text"

                def _key(rec):
                    vraw = (rec.get("fields") or {}).get(field)
                    if vraw is None or vraw == "":
                        return (1, "")
                    if ftype == "date":
                        d = _parse_date(vraw)
                        return (0, d or datetime(1900, 1, 1).date())
                    s_val = _to_lower_str(vraw)
                    return (0, s_val)

                records.sort(key=_key, reverse=(direction == "desc"))

        total = len(records)
        sliced = records[o:o + l]
        next_offset = str(o + l) if (o + l) < total else None
        return sliced, next_offset

    def query_table_records(self, table_name, base_label="main", offset=0, limit=100, search=None, filters=None, sorts=None):
        base_label = str(base_label or "main").strip().lower()
        table_name = str(table_name or "").strip()
        if not table_name:
            return [], None

        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT mt.table_key
                FROM mirror_tables mt
                WHERE mt.base_label=? AND mt.table_name=? AND mt.ignored=0
                LIMIT 1
                """,
                (base_label, table_name),
            )
            row = c.fetchone()
            if not row:
                return [], None
            table_key = row["table_key"]

            c.execute(
                "SELECT field_name, field_type FROM mirror_fields WHERE table_key=? ORDER BY field_name",
                (table_key,),
            )
            schema_rows = c.fetchall() or []

            c.execute(
                "SELECT airtable_id, fields_json, synced_ts FROM mirror_records WHERE table_key=? ORDER BY synced_ts DESC, airtable_id ASC",
                (table_key,),
            )
            raw_rows = c.fetchall() or []

        schema_types = {}
        for r in schema_rows:
            name = str(r["field_name"] or "").strip()
            typ = str(r["field_type"] or "").strip().lower()
            if not name:
                continue
            if "date" in typ or "time" in typ or typ in ("createdtime", "lastmodifiedtime"):
                schema_types[name] = "date"
            elif "number" in typ or "currency" in typ or "percent" in typ or typ == "count":
                schema_types[name] = "number"
            elif "select" in typ or "checkbox" in typ:
                schema_types[name] = "select"
            else:
                schema_types[name] = "text"

        def _to_lower_str(v):
            if v is None:
                return ""
            if isinstance(v, list):
                try:
                    return " ".join([str(x) for x in v]).lower()
                except Exception:
                    return str(v).lower()
            if isinstance(v, dict):
                try:
                    return json.dumps(v, ensure_ascii=False).lower()
                except Exception:
                    return str(v).lower()
            return str(v).lower()

        def _parse_date(v):
            if v is None:
                return None
            try:
                s = str(v).strip()
                if not s:
                    return None
                if "T" in s:
                    dt = _iso_to_dt(s)
                    return dt.date() if dt else None
                return datetime.fromisoformat(s.split(" ", 1)[0]).date()
            except Exception:
                try:
                    return datetime.fromisoformat(str(v)).date()
                except Exception:
                    return None

        def _eval_node(fields, cond):
            if not cond:
                return True
            if cond.get("isGroup") and isinstance(cond.get("conditions"), list):
                kids = cond.get("conditions") or []
                if not kids:
                    return True
                logic = str(cond.get("groupLogic") or "and").lower()
                out = _eval_node(fields, kids[0])
                for i in range(1, len(kids)):
                    child = _eval_node(fields, kids[i])
                    out = (out and child) if logic == "and" else (out or child)
                return out

            field = cond.get("field")
            op = cond.get("operator")
            if not field or not op:
                return True
            val_raw = (fields or {}).get(field)
            val = _to_lower_str(val_raw)
            cond_val = _to_lower_str(cond.get("value"))
            ftype = schema_types.get(field) or "text"

            if op == "contains":
                return cond_val in val
            if op == "does not contain":
                return cond_val not in val
            if op == "is":
                if ftype == "date":
                    d1 = _parse_date(val_raw)
                    d2 = _parse_date(cond.get("value"))
                    if d1 and d2:
                        return d1 == d2
                if isinstance(val_raw, list):
                    return any(_to_lower_str(x) == cond_val for x in val_raw)
                return val == cond_val
            if op == "is not":
                if isinstance(val_raw, list):
                    return all(_to_lower_str(x) != cond_val for x in val_raw)
                return val != cond_val
            if op == "is empty":
                return val == ""
            if op == "is not empty":
                return val != ""
            if op == "is before":
                d1 = _parse_date(val_raw)
                d2 = _parse_date(cond.get("value"))
                return bool(d1 and d2 and d1 < d2)
            if op == "is after":
                d1 = _parse_date(val_raw)
                d2 = _parse_date(cond.get("value"))
                return bool(d1 and d2 and d1 > d2)
            return True

        fs = filters if isinstance(filters, list) else []
        ss = sorts if isinstance(sorts, list) else []
        q = str(search or "").strip().lower()

        records = []
        for row in raw_rows:
            try:
                fields = json.loads(row["fields_json"] or "{}")
            except Exception:
                fields = {}
            if q:
                haystack = _to_lower_str(fields)
                if q not in haystack:
                    continue
            if fs:
                is_match = _eval_node(fields, fs[0])
                for i in range(1, len(fs)):
                    cm = _eval_node(fields, fs[i])
                    if str((fs[i] or {}).get("connector") or "and").lower() == "and":
                        is_match = is_match and cm
                    else:
                        is_match = is_match or cm
                if not is_match:
                    continue
            records.append({"id": row["airtable_id"], "fields": fields, "_synced_ts": int(row["synced_ts"] or 0)})

        for s in reversed(ss):
            field = str(s.get("field") or "").strip()
            direction = str(s.get("direction") or "asc").lower()
            if not field:
                continue
            ftype = schema_types.get(field) or "text"

            def _key(rec):
                vraw = (rec.get("fields") or {}).get(field)
                if vraw is None or vraw == "":
                    return (1, "")
                if ftype == "date":
                    d = _parse_date(vraw)
                    return (0, d or datetime(1900, 1, 1).date())
                if ftype == "number":
                    try:
                        return (0, float(vraw))
                    except Exception:
                        return (0, 0.0)
                return (0, _to_lower_str(vraw))

            records.sort(key=_key, reverse=(direction == "desc"))

        records = [{"id": r["id"], "fields": r["fields"]} for r in records]
        o = max(0, int(offset or 0))
        l = max(1, min(1000, int(limit or 100)))
        total = len(records)
        sliced = records[o:o + l]
        next_offset = str(o + l) if (o + l) < total else None
        return sliced, next_offset
