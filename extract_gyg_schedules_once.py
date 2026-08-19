"""One-time schedules/pricing extraction for all portal products."""

from __future__ import annotations

from scrape_gyg_portal import scrape_until_done


def main() -> None:
    scrape_until_done(schedules_only=True, rescrape_all=False)


if __name__ == "__main__":
    main()
