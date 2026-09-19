# FTS Travels — Partner Sandbox API (illustrative)

FTS Travels acts as the **supplier**. Your platform calls our HTTPS endpoints after the customer books on your side.

This environment is a **sandbox**:

- Demo products and demo prices only
- Confirmations look like `FTS-TEST-88421`
- **No live inventory and no Airtable writes**

Base URL: `https://crm.ftstravels.com`

Auth (all routes except health and OpenAPI):

```
Authorization: Bearer <sandbox-token>
```

`X-Api-Key: <sandbox-token>` is also accepted.

---

## Endpoints

| Method | Path | Auth |
|---|---|---|
| GET | `/partner/v1/health` | No |
| GET | `/partner/v1/openapi.json` | No |
| GET | `/partner/v1/products` | Yes |
| POST | `/partner/v1/availability` | Yes |
| POST | `/partner/v1/bookings` | Yes |
| GET | `/partner/v1/bookings/{vern_booking_id}` | Yes |

The same routes exist under `/api/partner/sandbox/...`.

---

## Availability

`POST /partner/v1/availability`

```json
{
  "product_id": "FTS-HUR-QUAD-001",
  "date": "2026-10-12",
  "pax": { "adults": 2, "children": 0 }
}
```

Response:

```json
{
  "available": true,
  "product_id": "FTS-HUR-QUAD-001",
  "date": "2026-10-12",
  "cutoff_hours": 12,
  "currency": "EUR",
  "price": { "adult": 45.0, "child": 30.0 },
  "sandbox": true
}
```

Same-day and past dates return `available: false` in this sandbox.

---

## Create booking

`POST /partner/v1/bookings`

Idempotent on `vern_booking_id`. Repeat posts return the same confirmation.

```json
{
  "vern_booking_id": "VERN-100245",
  "product_id": "FTS-HUR-QUAD-001",
  "date": "2026-10-12",
  "pickup_time": "08:00",
  "hotel_name": "Steigenberger Al Dau",
  "customer": {
    "first_name": "Anna",
    "last_name": "Schmidt",
    "email": "anna@example.com",
    "phone": "+491511234567"
  },
  "pax": { "adults": 2, "children": 0 }
}
```

Response `201`:

```json
{
  "status": "confirmed",
  "sandbox": true,
  "writes_to_airtable": false,
  "vern_booking_id": "VERN-100245",
  "fts_confirmation": "FTS-TEST-88421",
  "voucher_note": "SANDBOX ONLY — not a live booking. Please present this confirmation at pickup (test)."
}
```

---

## Demo product IDs

- `FTS-HUR-QUAD-001` — Quad Bike Desert Safari (Hurghada)
- `FTS-LXR-VALLEY-001` — Valley of the Kings (Luxor)
- `FTS-CAI-PYRAMIDS-001` — Giza Pyramids (Cairo)

Production product IDs, prices, and field names will follow **your** supplier specification after certification.
