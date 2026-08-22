"""
Airtable List (external + pickup) → FTS Transport partner jobs.

Phase 2: push operational jobs for OTA bookings that include hotel pickup.
Driver info from linked drivers table (LOCAL_DRIVER) is embedded in job notes.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

from airtable_fields import FieldIds, TABLE_NAME

DEFAULT_EXTERNAL_AGENCY_KEYWORDS = (
    "getyourguide",
    "gyg",
    "headout",
    "viator",
    "tiqets",
    "tripadvisor",
    "expedia",
    "klook",
    "civitatis",
    "musement",
    "bokun",
    "attraction",
    "tiqet",
)

DEFAULT_ACTIVE_STATUSES = ("active", "confirmed", "pending")
DEFAULT_SKIP_STATUSES = ("canceled", "cancelled", "cxl", "refund")

OTA_EMAIL_MARKERS = (
    "@reply.getyourguide.com",
    "@messaging.headout.com",
    "@guest.booking.com",
    "noreply@",
    "no-reply@",
    "donotreply",
)


def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _digits(s: Any) -> str:
    return re.sub(r"\D", "", str(s or ""))


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        if v is None or v == "":
            return default
        return int(float(v))
    except (TypeError, ValueError):
        return default


class TransportReferenceIndex:
    """In-memory index from GET /api/partner/reference."""

    def __init__(self, payload: Dict[str, Any]):
        self.raw = payload or {}
        locations = self.raw.get("locations") or []
        self.by_id: Dict[str, Dict[str, Any]] = {}
        self.hotels: List[Dict[str, Any]] = []
        self.zones: List[Dict[str, Any]] = []
        self.airports: List[Dict[str, Any]] = []
        for loc in locations:
            if not isinstance(loc, dict):
                continue
            lid = str(loc.get("id") or "").strip()
            if not lid:
                continue
            self.by_id[lid] = loc
            t = str(loc.get("type") or "").upper()
            if t == "HOTEL":
                self.hotels.append(loc)
            elif t == "ZONE":
                self.zones.append(loc)
            elif t == "AIRPORT":
                self.airports.append(loc)
        self.vehicle_types = list(self.raw.get("vehicleTypes") or [])

    def zone_for_hotel_id(self, hotel_id: str) -> Optional[str]:
        h = self.by_id.get(hotel_id)
        if not h:
            return None
        parent = str(h.get("parentId") or "").strip()
        if parent and self.by_id.get(parent, {}).get("type") == "ZONE":
            return parent
        return parent or None

    def match_hotel(self, hotel_name: str) -> Optional[Dict[str, Any]]:
        name_n = _norm(hotel_name)
        if not name_n:
            return None
        for h in self.hotels:
            if _norm(h.get("name")) == name_n:
                return h
        for h in self.hotels:
            hn = _norm(h.get("name"))
            if name_n in hn or hn in name_n:
                return h
        return None

    def airport_for_region(self, region_hint: str) -> Optional[Dict[str, Any]]:
        hint = _norm(region_hint)
        if not hint:
            return None
        for a in self.airports:
            an = _norm(a.get("name"))
            if hint in an or an in hint:
                return a
        if "sharm" in hint:
            for a in self.airports:
                if "sharm" in _norm(a.get("name")):
                    return a
        if "hurghada" in hint or "gharda" in hint:
            for a in self.airports:
                if "hurghada" in _norm(a.get("name")):
                    return a
        if "cairo" in hint:
            for a in self.airports:
                if "cairo" in _norm(a.get("name")):
                    return a
        return self.airports[0] if self.airports else None

    def default_zone_for_region(self, region_hint: str) -> Optional[Dict[str, Any]]:
        hint = _norm(region_hint)
        for z in self.zones:
            zn = _norm(z.get("name"))
            if hint and hint in zn:
                return z
        if "sharm" in hint:
            for z in self.zones:
                if "naama" in _norm(z.get("name")) or "sharm" in _norm(z.get("name")):
                    return z
        if "hurghada" in hint:
            for z in self.zones:
                if "hurghada" in _norm(z.get("name")) or "center" in _norm(z.get("name")):
                    return z
        if "cairo" in hint:
            for z in self.zones:
                if "downtown" in _norm(z.get("name")) or "cairo" in _norm(z.get("name")):
                    return z
        return self.zones[0] if self.zones else None

    def match_vehicle_type(self, car_label: str, pax: int) -> Optional[Dict[str, Any]]:
        label = _norm(car_label)
        best = None
        for vt in self.vehicle_types:
            if not vt.get("active", True):
                continue
            vn = _norm(vt.get("name"))
            if label and (label == vn or label in vn or vn in label):
                best = vt
                break
        if not best:
            for vt in self.vehicle_types:
                cap = _safe_int(vt.get("capacity"), 0)
                if cap >= pax:
                    best = vt
                    break
        if not best and self.vehicle_types:
            best = self.vehicle_types[0]
        return best


class TransportAirtableSync:
    def __init__(self, agent: Any):
        self.agent = agent
        self.script_dir = getattr(agent, "script_dir", os.path.dirname(os.path.abspath(__file__)))
        self.state_path = os.path.join(self.script_dir, "transport_sync_map.json")

    def transport_cfg(self) -> Dict[str, Any]:
        tc = (self.agent.config.get("transport") or {}) if isinstance(self.agent.config, dict) else {}
        return tc if isinstance(tc, dict) else {}

    def sync_cfg(self) -> Dict[str, Any]:
        return dict(self.transport_cfg().get("sync") or {})

    def api_base(self) -> str:
        return str(
            os.environ.get("TRANSPORT_API_URL")
            or self.transport_cfg().get("api_url")
            or ""
        ).strip().rstrip("/")

    def partner_key(self) -> str:
        return str(
            os.environ.get("TRANSPORT_PARTNER_KEY")
            or os.environ.get("PARTNER_API_KEY")
            or self.transport_cfg().get("partner_key")
            or ""
        ).strip()

    def load_state(self) -> Dict[str, Any]:
        try:
            if os.path.isfile(self.state_path):
                with open(self.state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
        except Exception as e:
            logging.warning("transport_sync: could not read state file: %s", e)
        return {"mappings": {}, "last_run": None}

    def save_state(self, state: Dict[str, Any]) -> None:
        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.warning("transport_sync: could not write state file: %s", e)

    def fetch_reference(self) -> TransportReferenceIndex:
        base = self.api_base()
        key = self.partner_key()
        if not base or not key:
            raise RuntimeError("TRANSPORT_API_URL / TRANSPORT_PARTNER_KEY not configured")
        resp = requests.get(
            f"{base}/api/partner/reference",
            headers={"X-Partner-Key": key},
            timeout=45,
        )
        if not resp.ok:
            raise RuntimeError(f"reference HTTP {resp.status_code}: {resp.text[:300]}")
        return TransportReferenceIndex(resp.json())

    def is_external_agency(self, agency: str) -> bool:
        cfg = self.sync_cfg()
        extra = cfg.get("agency_keywords") or cfg.get("agencies") or []
        keywords = list(DEFAULT_EXTERNAL_AGENCY_KEYWORDS)
        for item in extra:
            k = _norm(item)
            if k:
                keywords.append(k)
        ag = _norm(agency)
        if not ag:
            return False
        return any(k in ag for k in keywords)

    def booking_has_pickup_transfer(self, fields: Dict[str, Any]) -> bool:
        option = _norm(self.agent.get_field_value(fields, FieldIds.OPTION))
        addons_text = _norm(self.agent.get_field_value(fields, FieldIds.ADD_ONS_TEXT))
        addons_multi = self.agent.get_field_value(fields, FieldIds.ADD_ONS_MULTI) or []
        addons_combined = addons_text + " " + _norm(addons_multi)
        trip_name = _norm(self.agent.get_field_value(fields, FieldIds.TRIP_NAME))
        agency = _norm(self.agent.get_field_value(fields, FieldIds.AGENCY))
        pickup_time = self.agent.get_field_value(fields, FieldIds.PICKUP_TIME)
        hotel = self.agent.get_field_value(fields, FieldIds.HOTEL_NAME)

        has_kw = any(
            x in option or x in addons_combined
            for x in ("pickup", "transfer", "from hotel", "transport", "with guide", "guided tour")
        )
        no_transfer = any(
            x in option
            for x in ("ticket only", "no transfer", "meet at", "without transfer", "entry ticket", "admission")
        ) and not any(x in addons_combined for x in ("transfer", "pickup", "transport"))

        if has_kw:
            return True
        if no_transfer:
            return False
        if pickup_time or hotel:
            return True
        if any(x in trip_name for x in ("qr", "ticket", "meeting point")) or agency == "tiqets":
            return False
        return True

    def infer_region(self, fields: Dict[str, Any]) -> str:
        des = _norm(self.agent.get_field_value(fields, FieldIds.DES))
        hotel = _norm(self.agent.get_field_value(fields, FieldIds.HOTEL_NAME))
        trip = _norm(self.agent.get_field_value(fields, FieldIds.TRIP_NAME))
        blob = f"{des} {hotel} {trip}"
        if "sharm" in blob:
            return "sharm"
        if "hurghada" in blob or "gharda" in blob:
            return "hurghada"
        if "cairo" in blob or "giza" in blob:
            return "cairo"
        return des or "hurghada"

    def infer_service_type(self, fields: Dict[str, Any]) -> str:
        option = _norm(self.agent.get_field_value(fields, FieldIds.OPTION))
        from_loc = _norm(self.agent.get_field_value(fields, FieldIds.FROM_LOC))
        to_loc = _norm(self.agent.get_field_value(fields, FieldIds.TO_LOC))
        blob = f"{option} {from_loc} {to_loc}"
        if "airport" in blob and ("arrival" in blob or "arr" in blob):
            return "ARR"
        if "airport" in blob and ("departure" in blob or "dep" in blob):
            return "DEP"
        if "return" in blob and "transfer" in blob:
            return "RETURN"
        if "one way" in blob or "going" in blob:
            return "ONE_WAY_TRANSFER"
        return str(self.sync_cfg().get("default_service_type") or "DAY_TOUR")

    def resolve_driver_info(self, fields: Dict[str, Any]) -> Tuple[str, str]:
        linked = self.agent.get_field_value(fields, FieldIds.LOCAL_DRIVER)
        drivers_table = getattr(self.agent, "drivers_table", None)
        if isinstance(linked, list) and linked and drivers_table:
            try:
                rec = drivers_table.get(linked[0])
                f = (rec or {}).get("fields") or {}
                name = str(f.get("Driver Name") or "").strip()
                phone = str(f.get("Phone Number") or "").strip()
                if name or phone:
                    return name, phone
            except Exception as e:
                logging.warning("transport_sync: driver link fetch failed: %s", e)
        if isinstance(linked, list) and linked:
            # Linked field present but driver row not resolved — omit raw record ids from notes.
            pass
        raw = str(self.agent.get_field_value(fields, FieldIds.DRIVER_NAME_PHONE) or "").strip()
        if raw:
            return raw, ""
        return "", ""

    def guest_email(self, fields: Dict[str, Any], booking_nr: str) -> str:
        for fid in (FieldIds.CUSTOMER_PERSONAL_EMAIL, FieldIds.CUSTOMER_EMAIL):
            raw = str(self.agent.get_field_value(fields, fid) or "").strip().lower()
            if not raw or "@" not in raw:
                continue
            if any(m in raw for m in OTA_EMAIL_MARKERS):
                continue
            return raw
        safe_nr = re.sub(r"[^a-zA-Z0-9]", "", booking_nr or "booking")
        return f"transport+{safe_nr}@ftstravels.com"

    def guest_phone(self, fields: Dict[str, Any]) -> str:
        raw = _digits(self.agent.get_field_value(fields, FieldIds.CUSTOMER_PHONE))
        if len(raw) >= 8:
            return raw
        return "20000000000"

    def parse_job_date(self, fields: Dict[str, Any]) -> Optional[str]:
        raw = self.agent.get_field_value(fields, FieldIds.DATE_TRIP)
        if not raw:
            return None
        try:
            if isinstance(raw, str) and "T" in raw:
                return raw.split("T")[0]
            if hasattr(self.agent, "get_corrected_trip_date"):
                d, _ = self.agent.get_corrected_trip_date(raw)
                if d:
                    return d.isoformat()
        except Exception:
            pass
        return None

    def parse_pickup_iso(self, fields: Dict[str, Any], job_date: str) -> Optional[str]:
        pt = str(self.agent.get_field_value(fields, FieldIds.PICKUP_TIME) or "").strip()
        if not pt or not job_date:
            return None
        m = re.match(r"^(\d{1,2}):(\d{2})", pt)
        if not m:
            return None
        hh, mm = int(m.group(1)), int(m.group(2))
        try:
            dt = datetime.strptime(job_date, "%Y-%m-%d").replace(hour=hh, minute=mm)
            return dt.isoformat()
        except ValueError:
            return None

    def resolve_zones(
        self,
        fields: Dict[str, Any],
        index: TransportReferenceIndex,
        service_type: str,
    ) -> Tuple[str, str, Optional[str], Optional[str], Optional[str]]:
        region = self.infer_region(fields)
        hotel_name = str(self.agent.get_field_value(fields, FieldIds.HOTEL_NAME) or "").strip()
        hotel_row = index.match_hotel(hotel_name)
        hotel_id = str(hotel_row.get("id") or "") if hotel_row else None
        zone_id = index.zone_for_hotel_id(hotel_id) if hotel_id else None
        if not zone_id:
            z = index.default_zone_for_region(region)
            zone_id = str(z.get("id") or "") if z else None
        airport = index.airport_for_region(region)
        airport_id = str(airport.get("id") or "") if airport else None

        if not zone_id:
            raise RuntimeError(f"Could not resolve zone for hotel={hotel_name!r} region={region}")

        if service_type == "ARR":
            return airport_id or zone_id, zone_id, hotel_id, airport_id, None
        if service_type == "DEP":
            return zone_id, airport_id or zone_id, hotel_id, None, airport_id
        return zone_id, zone_id, hotel_id, None, None

    def build_partner_payload(
        self,
        record: Dict[str, Any],
        index: TransportReferenceIndex,
    ) -> Dict[str, Any]:
        fields = record.get("fields") or {}
        booking_nr = str(self.agent.get_field_value(fields, FieldIds.BOOKING_NR) or record.get("id") or "").strip()
        if not booking_nr:
            raise RuntimeError("Missing booking number")

        job_date = self.parse_job_date(fields)
        if not job_date:
            raise RuntimeError("Missing or invalid Date Trip")

        service_type = self.infer_service_type(fields)
        from_zone, to_zone, hotel_id, origin_airport, dest_airport = self.resolve_zones(
            fields, index, service_type
        )

        adt = _safe_int(self.agent.get_field_value(fields, FieldIds.ADT))
        chd = _safe_int(self.agent.get_field_value(fields, FieldIds.CHD))
        inf = _safe_int(self.agent.get_field_value(fields, FieldIds.INF))
        pax = adt + chd + inf
        if pax <= 0:
            pax = _safe_int(self.agent.get_field_value(fields, FieldIds.TOTAL_TRAVELERS), 1)
        pax = max(1, pax)

        car_label = (
            str(self.agent.get_field_value(fields, FieldIds.CAR_TYPE) or "")
            or str(self.agent.get_field_value(fields, FieldIds.LOCAL_CAR_TYPE) or "")
        ).strip()
        vehicle = index.match_vehicle_type(car_label, pax)
        if not vehicle:
            raise RuntimeError(f"No vehicle type for pax={pax} car={car_label!r}")

        driver_name, driver_phone = self.resolve_driver_info(fields)
        notes_parts = [
            f"Airtable record {record.get('id')}",
            f"Agency: {self.agent.get_field_value(fields, FieldIds.AGENCY) or ''}",
            f"Trip: {self.agent.get_field_value(fields, FieldIds.TRIP_NAME) or ''}",
            f"Option: {self.agent.get_field_value(fields, FieldIds.OPTION) or ''}",
        ]
        if driver_name or driver_phone:
            notes_parts.append(f"Driver: {driver_name} {driver_phone}".strip())
        room = str(self.agent.get_field_value(fields, FieldIds.ROOM_NUMBER) or "").strip()
        if room:
            notes_parts.append(f"Room: {room}")
        remarks = str(self.agent.get_field_value(fields, FieldIds.REMARKS) or "").strip()
        if remarks:
            notes_parts.append(f"Remarks: {remarks}")

        currency = str(self.agent.get_field_value(fields, FieldIds.CURRENCY) or "EGP").strip() or "EGP"
        amount = _safe_float(self.agent.get_field_value(fields, FieldIds.AMOUNT), 0.0)

        payload: Dict[str, Any] = {
            "b2cBookingRef": f"fts-{booking_nr}",
            "serviceType": service_type,
            "jobDate": job_date,
            "pickupTime": self.parse_pickup_iso(fields, job_date),
            "fromZoneId": from_zone,
            "toZoneId": to_zone,
            "paxCount": pax,
            "vehicleTypeId": str(vehicle.get("id")),
            "guestName": str(self.agent.get_field_value(fields, FieldIds.CUSTOMER_NAME) or "Guest").strip(),
            "guestEmail": self.guest_email(fields, booking_nr),
            "guestPhone": self.guest_phone(fields),
            "guestCountry": str(self.agent.get_field_value(fields, FieldIds.CUSTOMER_COUNTRY) or "").strip() or None,
            "paymentMethod": str(self.sync_cfg().get("payment_method") or "ONLINE"),
            "total": amount,
            "currency": currency,
            "notes": "\n".join(notes_parts),
        }
        if hotel_id:
            payload["hotelId"] = hotel_id
        if origin_airport:
            payload["originAirportId"] = origin_airport
        if dest_airport:
            payload["destinationAirportId"] = dest_airport
        hotel_addr = str(self.agent.get_field_value(fields, FieldIds.HOTEL_NAME) or "").strip()
        if hotel_addr:
            payload["pickupAddress"] = hotel_addr
        return payload

    def push_job(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        base = self.api_base()
        key = self.partner_key()
        resp = requests.post(
            f"{base}/api/partner/jobs",
            headers={"X-Partner-Key": key, "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text[:500]}
        if not resp.ok:
            raise RuntimeError(f"partner/jobs HTTP {resp.status_code}: {body}")
        return body

    def booking_status_ok(self, fields: Dict[str, Any]) -> bool:
        status = _norm(self.agent.get_field_value(fields, FieldIds.BOOKING_STATUS))
        if not status:
            return True
        cfg_allow = [ _norm(x) for x in (self.sync_cfg().get("booking_status_allow") or DEFAULT_ACTIVE_STATUSES) ]
        cfg_skip = [ _norm(x) for x in (self.sync_cfg().get("booking_status_skip") or DEFAULT_SKIP_STATUSES) ]
        if any(s in status for s in cfg_skip):
            return False
        if cfg_allow:
            return any(s in status for s in cfg_allow)
        return True

    def should_sync_record(self, record: Dict[str, Any]) -> Tuple[bool, str]:
        fields = record.get("fields") or {}
        agency = str(self.agent.get_field_value(fields, FieldIds.AGENCY) or "")
        if not self.is_external_agency(agency):
            return False, "not_external_agency"
        if not self.booking_has_pickup_transfer(fields):
            return False, "no_pickup_transfer"
        if not self.booking_status_ok(fields):
            return False, "booking_status_skip"
        if not self.parse_job_date(fields):
            return False, "missing_date_trip"
        if not str(self.agent.get_field_value(fields, FieldIds.HOTEL_NAME) or "").strip():
            return False, "missing_hotel"
        return True, "ok"

    def list_candidates(
        self,
        max_records: int = 50,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        booking_nr: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        table = getattr(self.agent, "table", None)
        if not table:
            raise RuntimeError("Main List table not connected")

        cap = max(1, min(int(max_records or 50), 500))

        if booking_nr:
            safe = str(booking_nr).replace("'", "\\'")
            field_name = "Booking Nr."
            formula = f"{{{field_name}}}='{safe}'"
            records = table.all(formula=formula, max_records=5)
            return list(records or [])

        formula_parts: List[str] = []
        if date_from and date_to and date_from == date_to:
            formula_parts.append(f"IS_SAME({{Date Trip}}, '{date_from}', 'day')")
        else:
            if date_from:
                formula_parts.append(f"IS_AFTER({{Date Trip}}, '{date_from}')")
            if date_to:
                formula_parts.append(f"IS_BEFORE({{Date Trip}}, '{date_to}')")
        formula = "AND(" + ",".join(formula_parts) + ")" if len(formula_parts) > 1 else (formula_parts[0] if formula_parts else None)

        if formula:
            try:
                records = table.all(formula=formula, max_records=cap)
                return list(records or [])
            except Exception as e:
                logging.warning("transport_sync: Airtable date formula failed, falling back to scan: %s", e)

        records = table.all(max_records=cap)
        out: List[Dict[str, Any]] = []
        for rec in records or []:
            fields = rec.get("fields") or {}
            jd = self.parse_job_date(fields)
            if date_from and jd and jd < date_from:
                continue
            if date_to and jd and jd > date_to:
                continue
            out.append(rec)
        return out

    def run(
        self,
        dry_run: bool = True,
        max_records: int = 25,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        booking_nr: Optional[str] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        if not self.sync_cfg().get("enabled", True):
            return {"status": "skipped", "message": "transport.sync.enabled is false"}

        state = self.load_state()
        mappings = state.get("mappings") or {}
        index = self.fetch_reference()
        records = self.list_candidates(max_records, date_from, date_to, booking_nr)

        results: List[Dict[str, Any]] = []
        pushed = 0
        skipped = 0
        errors = 0

        for rec in records:
            rid = str(rec.get("id") or "")
            fields = rec.get("fields") or {}
            bnr = str(self.agent.get_field_value(fields, FieldIds.BOOKING_NR) or rid)
            key = f"fts-{bnr}"

            ok, reason = self.should_sync_record(rec)
            if not ok:
                skipped += 1
                results.append({"record_id": rid, "booking_nr": bnr, "status": "skip", "reason": reason})
                continue

            if not force and key in mappings:
                skipped += 1
                results.append({
                    "record_id": rid,
                    "booking_nr": bnr,
                    "status": "skip",
                    "reason": "already_synced",
                    "transport_job": mappings[key],
                })
                continue

            try:
                payload = self.build_partner_payload(rec, index)
                if dry_run:
                    results.append({
                        "record_id": rid,
                        "booking_nr": bnr,
                        "status": "preview",
                        "payload": payload,
                    })
                    continue
                resp = self.push_job(payload)
                mappings[key] = {
                    "record_id": rid,
                    "booking_nr": bnr,
                    "synced_at": datetime.now(timezone.utc).isoformat(),
                    "response": resp,
                }
                pushed += 1
                results.append({
                    "record_id": rid,
                    "booking_nr": bnr,
                    "status": "pushed",
                    "transport_job": resp,
                })
            except Exception as e:
                errors += 1
                logging.error("transport_sync record %s failed: %s", bnr, e, exc_info=True)
                results.append({
                    "record_id": rid,
                    "booking_nr": bnr,
                    "status": "error",
                    "message": str(e),
                })

        if not dry_run:
            state["mappings"] = mappings
            state["last_run"] = datetime.now(timezone.utc).isoformat()
            self.save_state(state)

        return {
            "status": "success",
            "dry_run": dry_run,
            "table": TABLE_NAME,
            "scanned": len(records),
            "pushed": pushed,
            "skipped": skipped,
            "errors": errors,
            "results": results,
        }
