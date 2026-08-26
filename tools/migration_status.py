"""Quick migration status check (no credentials printed)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.migrate_airtable_to_baserow import BaserowApi, load_config, load_state  # noqa: E402

LOGS = [
    Path(r"C:\Users\Aloosh2020\migrate_list_fresh.log"),
    Path(r"C:\Users\Aloosh2020\migrate_all.log"),
]


def running_migrate_pids() -> list[int]:
    ps = r"""
Get-CimInstance Win32_Process |
  Where-Object { $_.Name -match '^python(\.exe)?$' -and $_.CommandLine -like '*migrate_airtable_to_baserow*' } |
  Select-Object -ExpandProperty ProcessId
"""
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
        timeout=30,
    )
    pids = []
    for line in (out.stdout or "").splitlines():
        line = line.strip()
        if line.isdigit():
            pids.append(int(line))
    return pids


def tail_log(path: Path, n: int = 8) -> list[str]:
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-n:]


def main() -> int:
    print("=== FTS Migration Status ===\n")

    pids = running_migrate_pids()
    if pids:
        print(f"PROCESS: RUNNING  PIDs={pids}")
    else:
        print("PROCESS: STOPPED (no migrate_airtable_to_baserow)")

    state = load_state()
    tables = state.get("tables") or {}
    complete = sum(1 for t in tables.values() if t.get("complete"))
    incomplete = [n for n, t in tables.items() if not t.get("complete")]
    print(f"STATE: {len(tables)} tables tracked | complete={complete} | incomplete={len(incomplete)}")
    if incomplete:
        print("  incomplete:", ", ".join(incomplete))

    lst = tables.get("List") or {}
    if lst:
        print(
            f"  List: id={lst.get('baserow_table_id')} "
            f"synced={lst.get('records_synced')} complete={lst.get('complete')}"
        )

    try:
        cfg = load_config()
        br = BaserowApi.from_config(cfg["baserow"])
        db_id = int(cfg["baserow"].get("database_id") or 1)
        t = br.find_table_by_name(db_id, "List")
        if t:
            tid = int(t["id"])
            rows = br._req("GET", f"/api/database/rows/table/{tid}/?size=1")
            print(f"BASEROW List: id={tid} rows={rows.get('count')}")
        else:
            print("BASEROW List: NOT FOUND")
    except Exception as exc:
        print(f"BASEROW check skipped: {exc}")

    for log in LOGS:
        tail = tail_log(log)
        if tail:
            print(f"\nLOG tail ({log.name}):")
            for line in tail:
                print(f"  {line}")
            break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
