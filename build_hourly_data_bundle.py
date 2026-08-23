#!/usr/bin/env python3
"""Build a restore zip of live CRM data without stopping the server."""
from __future__ import annotations

import glob
import os
import shutil
import sqlite3
import sys
import zipfile
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
BUNDLE_DIR = os.path.join(ROOT, "hourly_data_backup")
STAGE_DIR = os.path.join(BUNDLE_DIR, "stage")
ZIP_PATH = os.path.join(BUNDLE_DIR, "fts_crm_data_latest.zip")

SQLITE_FILES = [
    "chat_history.db",
    "airtable_mirror.db",
]

SECRET_FILES = [
    "config.json",
    "railway_vars.json",
    "token.json",
    "token_sales.json",
    "credentials.json",
    "credentials_sales.json",
    "google_reviews_token.json",
]

STATE_FILES = [
    "learned_corrections.json",
    "hajj_tahseen_followup_state.json",
    "hajj_5ads_followup_state.json",
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


def collect_secret_globs() -> list[str]:
    names = list(SECRET_FILES)
    names.extend(
        os.path.basename(path)
        for path in glob.glob(os.path.join(ROOT, "client_secret_*.json"))
    )
    names.extend(
        os.path.basename(path)
        for path in glob.glob(os.path.join(ROOT, "token*.json"))
    )
    names.extend(
        os.path.basename(path)
        for path in glob.glob(os.path.join(ROOT, "credentials*.json"))
    )
    unique = []
    seen = set()
    for name in names:
        if name not in seen:
            unique.append(name)
            seen.add(name)
    return unique


def main() -> int:
    os.makedirs(BUNDLE_DIR, exist_ok=True)
    if os.path.isdir(STAGE_DIR):
        shutil.rmtree(STAGE_DIR)
    os.makedirs(STAGE_DIR, exist_ok=True)

    copied = []
    missing = []

    for name in SQLITE_FILES:
        src = os.path.join(ROOT, name)
        dst = os.path.join(STAGE_DIR, name)
        if not os.path.exists(src):
            missing.append(name)
            continue
        backup_sqlite(src, dst)
        copied.append(name)

    for name in collect_secret_globs() + STATE_FILES:
        src = os.path.join(ROOT, name)
        dst = os.path.join(STAGE_DIR, name)
        if not os.path.exists(src):
            if name not in missing:
                missing.append(name)
            continue
        shutil.copy2(src, dst)
        copied.append(name)

    if not copied:
        print("ERROR=nothing_to_bundle")
        return 1

    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in copied:
            zf.write(os.path.join(STAGE_DIR, name), arcname=name)

    size = os.path.getsize(ZIP_PATH)
    manifest = os.path.join(BUNDLE_DIR, "MANIFEST.txt")
    with open(manifest, "w", encoding="utf-8") as fh:
        fh.write("created_at={0}\n".format(datetime.now().strftime("%Y%m%d-%H%M%S")))
        fh.write("zip_bytes={0}\n".format(size))
        fh.write("copied:\n")
        for name in copied:
            fh.write("  - {0}\n".format(name))
        fh.write("missing:\n")
        for name in missing:
            fh.write("  - {0}\n".format(name))

    print("ZIP={0}".format(ZIP_PATH))
    print("BYTES={0}".format(size))
    print("COPIED={0}".format(len(copied)))
    print("MISSING={0}".format(len(missing)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
