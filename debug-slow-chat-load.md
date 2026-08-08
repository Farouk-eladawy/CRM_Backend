[OPEN] Debug Session: slow-chat-load

## Symptom
- Selecting a chat causes messages to appear after ~1 minute.

## Environment
- OS: Windows
- Backend: Flask (ai_agent.py)
- Frontend: React/Vite (frontend_dashboard/new_frontend_dashboard)

## Hypotheses
1) Frontend polling/timers are set to ~60s or blocked by re-renders, so messages fetch is delayed.
2) Backend /api/chats/<chat_id> is slow due to SQLite locks (WAL contention) or a long-running transaction.
3) The frontend does heavy client-side processing (merge/sort/dedupe) on a large message set, delaying render.
4) Network errors/retries/backoff cause effective delay (e.g., failed fetch then retry later).
5) Backend returns fast but UI state gating prevents showing results until a later tick (race/abort logic).

## Evidence to Collect
- Timing of: click chat → request start → response received → UI state setMessages → UI render.
- Backend request duration for /api/chats/<chat_id> and /api/chats.
- SQLite lock occurrences around get_messages/unread updates.

## Plan
- Add instrumentation (non-business) in frontend + backend to report timings to Debug Server.
- Reproduce once, analyze logs, then apply minimal fix.

