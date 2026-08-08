[OPEN] Airtable chat log 403

## Session
- session_id: airtable-chat-log-403
- created_at: 2026-07-13
- scope: Investigate Airtable 403 in append_to_chat_log without modifying business logic before evidence.

## Symptoms
- Backend alert reports `403 Client Error: Forbidden` while PATCH/UPDATE targeting Airtable record `recTPeOaOPg4L1K7v` in table `List`.
- Error originates from `ai_agent.py:2962` inside `append_to_chat_log`.

## Hypotheses
1. The configured Airtable base ID or table target is wrong for this write path.
2. The API token in runtime lacks write permission to base `appTp5YgSp9DV2HYc` or table `List`.
3. The record ID belongs to a different base/table than the configured one.
4. `append_to_chat_log` is using the wrong Airtable endpoint/model name for the current schema.
5. Runtime config/environment differs from the checked-in `config.json`, causing writes to an unintended base.

## Evidence Log
- `append_to_chat_log` fetches then updates via `table.get(record_id)` and `table.update(record_id, update_data, typecast=True)`.
- `load_config()` reads `config.json` from project root directly; no Airtable env override was found for this path.
- Direct runtime probe against `https://api.airtable.com/v0/appTp5YgSp9DV2HYc/List/recTPeOaOPg4L1K7v` returned `403` for both `GET` and `PATCH`.
- Because `GET` already fails, the issue is not caused by the appended chat log payload.

## Next Steps
1. Confirm whether `List` still exists in base `appTp5YgSp9DV2HYc` and whether the PAT has base/table access.
2. Confirm whether record `recTPeOaOPg4L1K7v` belongs to this base/table.
3. If permissions were recently changed, rotate/update the Airtable PAT and restart the backend.
