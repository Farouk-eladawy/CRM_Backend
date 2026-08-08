#!/usr/bin/env python3
"""
Create a consistent SQLite snapshot for Railway staging/upload
WITHOUT stopping the local CRM process.

Uses SQLite online backup API (safe while DB is in use).
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(ROOT, "railway_staging_upload")

SOURCE_FILES = [
    "chat_history.db",
    "learned_corrections.json",
    "hajj_tahseen_followup_state.json",
    "religious_15day_followup_state.json",
    "religious_umrah_8day_followup_state.json",
    "religious_umrah_10day_followup_state.json",
    "religious_hajj_earlybooking_followup_state.json",
    "sales_reminder_state.json",
]


def backup_sqlite(src_path: str, dst_path: str) -> None:
    if os.path.exists(dst_path):
        os.remove(dst_path)
    src = sqlite3.connect(src_path, timeout=60.0)
    try:
        dst = sqlite3.connect(dst_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def main() -> int:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    copied = []
    missing = []

    for name in SOURCE_FILES:
        src = os.path.join(ROOT, name)
        if not os.path.exists(src):
            missing.append(name)
            continue
        dst = os.path.join(UPLOAD_DIR, name)
        if name.endswith(".db"):
            print(f"[SNAPSHOT] SQLite backup: {name}")
            backup_sqlite(src, dst)
        else:
            print(f"[COPY] {name}")
            shutil.copy2(src, dst)
        copied.append(name)

    manifest = os.path.join(UPLOAD_DIR, "MANIFEST.txt")
    with open(manifest, "w", encoding="utf-8") as fh:
        fh.write(f"created_at={stamp}\n")
        fh.write("mode=staging_snapshot_local_still_running\n")
        fh.write("copied:\n")
        for name in copied:
            fh.write(f"  - {name}\n")
        fh.write("missing:\n")
        for name in missing:
            fh.write(f"  - {name}\n")

    print("")
    print(f"[OK] Snapshot ready in: {UPLOAD_DIR}")
    print(f"[OK] Copied {len(copied)} file(s). Missing {len(missing)} file(s).")
    if not copied:
        print("[ERROR] Nothing copied. Is chat_history.db present?")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
