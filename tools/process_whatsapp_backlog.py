import argparse
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--min-age", type=int, default=15)
    parser.add_argument("--max-age", type=int, default=21600)
    args = parser.parse_args(argv[1:])

    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from ai_agent import AIAgent

    agent = AIAgent()
    processed = agent.process_unread_whatsapp_auto_replies(
        limit=args.limit,
        min_age_seconds=args.min_age,
        max_age_seconds=args.max_age,
    )
    print(f"processed={int(processed or 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

