# Debug Session: religious-lead-linking [OPEN]

## Scope
- Prevent unsafe chat unlinking caused by weak booking extraction.
- Diagnose incorrect lead creation in the Religious inquiries table.

## Symptoms
- Logs show `Checking Booking Nr (WEAK): QUALITY`.
- Logs show `changing link from <record_id> to  based on explicit booking number`.
- Logs show creation of a new Religious lead after failed strict lookup.

## Hypotheses
1. Weak booking extraction is treated as explicit booking evidence.
2. Existing linked chats are allowed to clear `airtable_record_id` when lookup returns no record.
3. Religious lead creation does not guard against already-linked chats.
4. Facebook fallback path promotes phone-only messages into new Religious leads too aggressively.
5. Existing conversation context is ignored during post-lookup fallback.

## Evidence To Collect
- Where `Checking Booking Nr (WEAK)` is emitted.
- How `explicit_booking_nr` is produced and validated.
- Whether `record_id_to_save` can become empty while `has_explicit_new_booking` is true.
- Whether `create_lead_record(... department="religious")` is called even when a protected linked conversation exists.

## Status
- Investigating code path and collecting static/runtime evidence.

## Evidence Found
- `extract_booking_numbers_regex()` classifies all-caps words as `WEAK` booking candidates.
- `_is_placeholder_booking_number()` does not exclude `quality`.
- The relinking path previously consumed the first non-placeholder candidate as `explicit_booking_nr` without requiring `STRONG` confidence or a matched record.
- This allowed logs such as `Checking Booking Nr (WEAK): QUALITY` to influence relinking protection.
- Once `booking_record` remained `None`, the generic lead fallback created a new Religious lead in `استفسارات جديدة`.

## Fix Applied
- Added `_get_verified_explicit_booking_number()` to only accept `STRONG` booking candidates.
- The helper also requires a real matched record before a candidate can authorize relinking.
- Updated both conversation update paths to use the verified helper instead of the raw first candidate.

## Expected Post-Fix Behavior
- `QUALITY` or similar `WEAK` tokens no longer count as explicit booking numbers.
- Existing linked chats keep their `airtable_record_id` unless a real strong booking match exists.
- Religious lead creation should no longer trigger from this weak-token unlinking path.
