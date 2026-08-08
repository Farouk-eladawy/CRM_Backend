# [OPEN] session-dashboard-users

## Symptom
- Religious Admin/Manager sees foreign users in `Daily Session Dashboard` employee dropdown.
- Some expected Religious users are missing.

## Expected
- Religious Admin/Manager should only see employees belonging to the Religious department/team.
- Primary admin (admin manager) keeps full visibility.

## Hypotheses
1. Production is still serving old frontend/backend build (or cached response), so actor team filtering is not applied.
2. Frontend does not send `actor.allowed_locations`, so backend cannot filter users by department and returns full list.
3. Backend sources `available_users` from `users.json`/users_map, not `dashboard_users`, so newly added employees are missing.
4. Some missing employees have `role = AI` (excluded), or lack `allowedLocations` mapping, so they are filtered out unintentionally.
5. Cached session-dashboard payload (server cache / localStorage cache) is reused and contains stale `available_users`.

## Evidence Needed
- Request payload + response body for `POST /api/dashboard/session-daily`.
- `localStorage.currentUser` value for the affected account.
- Whether the missing employees exist in `dashboard_users` setting and/or `users.json`.

