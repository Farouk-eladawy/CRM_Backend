import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import chat_db  # noqa: E402


KNOWN_GUIDES = {
    "201005138825": "AHMED HASSAN",
    "201008841924": "MOHAMED HASSAN",
    "201099405492": "Hoda italian",
}


def main() -> int:
    repaired = chat_db.repair_guide_conversations_by_phone(KNOWN_GUIDES)
    print(json.dumps({"repaired": repaired, "count": len(repaired)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
