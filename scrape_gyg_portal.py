"""Scrape missing GYG supplier portal products — auto-restart browser on logout."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone

from playwright.sync_api import BrowserContext, Page, Playwright, sync_playwright

from build_gyg_products_from_portal import (
    LIST_URL,
    PORTAL_CATALOG_FILE,
    PRODUCTS_FILE,
    _save_outputs,
    build_api_product,
    scrape_product_details,
    scrape_product_list,
    scrape_product_schedules,
)
from gyg_portal_auth import (
    STATE_FILE,
    ensure_session,
    human_pause,
    is_authenticated,
    is_login_page,
    launch_firefox_context,
    save_session,
    _load_credentials,
)

MAX_BROWSER_RESTARTS = 20  # per run
MAX_RETRIES_PER_PRODUCT = 8


class SessionLostError(Exception):
    pass


def load_catalog() -> tuple[dict, list[dict]]:
    if os.path.isfile(PORTAL_CATALOG_FILE):
        with open(PORTAL_CATALOG_FILE, encoding="utf-8") as handle:
            doc = json.load(handle)
        return doc, list(doc.get("products") or [])
    return {"scraped_at": "", "source": LIST_URL, "count": 0, "products": []}, []


def rebuild_api_products(catalog: list[dict]) -> list[dict]:
    out = []
    for row in catalog:
        if not row.get("details_loaded"):
            continue
        list_row = {
            "title": row.get("title") or row.get("product_title") or "",
            "reference": row.get("reference_code") or row.get("reference") or "",
            "gyg_tour_id": row.get("gyg_tour_id"),
            "rating": row.get("rating") or "Not rated",
            "status": row.get("status") or "Bookable",
            "public_url": row.get("public_url") or "",
            "supplier_url": row.get("supplier_url") or "",
        }
        out.append(build_api_product(list_row, row))
    return out


def save_progress(catalog_doc: dict, catalog: list[dict]) -> None:
    catalog_doc["scraped_at"] = datetime.now(timezone.utc).isoformat()
    catalog_doc["source"] = LIST_URL
    catalog_doc["count"] = len(catalog)
    catalog_doc["products"] = catalog
    _save_outputs(catalog, rebuild_api_products(catalog))
    loaded = sum(1 for p in catalog if p.get("details_loaded"))
    print(f"  Saved: {loaded}/{len(catalog)} -> {PRODUCTS_FILE}")


class BrowserSession:
    def __init__(self, playwright: Playwright, creds: dict[str, str]) -> None:
        self.playwright = playwright
        self.creds = creds
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.restart_count = 0

    def start(self) -> None:
        self.close(save=False)
        print("\n>>> Opening Edge...")
        self.context = launch_firefox_context(self.playwright)
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        ensure_session(self.page, self.context, self.creds)
        print(">>> Session ready.\n")

    def restart(self) -> None:
        self.restart_count += 1
        if self.restart_count > MAX_BROWSER_RESTARTS:
            raise RuntimeError(f"Too many browser restarts ({MAX_BROWSER_RESTARTS})")
        print(f"\n{'=' * 60}")
        print(f"  LOGOUT DETECTED — restart #{self.restart_count}")
        print("  Closing browser, reopening, auto-login, continuing...")
        print(f"{'=' * 60}\n")
        human_pause(4, 7)
        self.start()

    def close(self, save: bool = True) -> None:
        if not self.context:
            return
        try:
            if save:
                save_session(self.context)
        except Exception:
            pass
        try:
            self.context.close()
        except Exception:
            pass
        self.context = None
        self.page = None

    def scrape_one(self, tour_id: str) -> dict:
        assert self.page is not None
        if is_login_page(self.page) or not is_authenticated(self.page):
            raise SessionLostError("login page before navigation")
        details = scrape_product_details(self.page, tour_id, self.context, self.creds)
        if is_login_page(self.page) or not is_authenticated(self.page):
            raise SessionLostError("redirected to login after scrape")
        if not details.get("details_loaded"):
            raise SessionLostError("product page did not load")
        return details

    def scrape_schedules_one(self, tour_id: str, catalog_row: dict | None = None) -> dict:
        assert self.page is not None
        if is_login_page(self.page) or not is_authenticated(self.page):
            raise SessionLostError("login page before navigation")
        option_ids = [
            str(opt.get("option_id"))
            for opt in ((catalog_row or {}).get("options") or [])
            if opt.get("option_id")
        ]
        schedule_data = scrape_product_schedules(
            self.page,
            tour_id,
            self.context,
            self.creds,
            known_option_ids=option_ids,
        )
        if is_login_page(self.page):
            raise SessionLostError("redirected to login after schedule scrape")
        has_schedules = any(
            opt.get("schedules")
            for opt in (schedule_data.get("option_schedules") or [])
        )
        if not has_schedules:
            raise SessionLostError("schedules did not load")
        return schedule_data


def _needs_schedule_scrape(row: dict) -> bool:
    if not row.get("gyg_tour_id"):
        return False
    option_schedules = row.get("option_schedules") or []
    if not option_schedules:
        return True
    return not any(opt.get("schedules") for opt in option_schedules)


def pending_products(
    catalog: list[dict],
    rescrape_all: bool,
    missing_inclusions_only: bool = False,
    schedules_only: bool = False,
) -> list[dict]:
    if schedules_only:
        return [
            row for row in catalog
            if row.get("gyg_tour_id") and (rescrape_all or _needs_schedule_scrape(row))
        ]
    if missing_inclusions_only:
        return [
            row for row in catalog
            if row.get("gyg_tour_id") and len(row.get("inclusions") or []) == 0
        ]
    return [
        row for row in catalog
        if row.get("gyg_tour_id") and (rescrape_all or not row.get("details_loaded"))
    ]


def scrape_until_done(
    rescrape_all: bool = False,
    missing_inclusions_only: bool = False,
    schedules_only: bool = False,
) -> None:
    creds = _load_credentials()
    if not creds.get("email"):
        raise RuntimeError("Missing gyg_portal_credentials.json — cannot auto-login.")

    with sync_playwright() as p:
        session = BrowserSession(p, creds)
        session.start()

        try:
            catalog_doc, catalog = load_catalog()
            if not catalog:
                assert session.page is not None
                catalog = scrape_product_list(session.page)
                catalog_doc["products"] = catalog
                save_progress(catalog_doc, catalog)

            pending = pending_products(
                catalog, rescrape_all, missing_inclusions_only, schedules_only
            )
            if not pending:
                print("Nothing to scrape.")
            else:
                total = len(catalog)
                if schedules_only:
                    print(f"\nSchedules/pricing: {len(pending)} products to scrape\n")
                elif missing_inclusions_only:
                    print(f"\nMissing inclusions: {len(pending)} products to enrich\n")
                else:
                    done = total - len(pending)
                    print(f"\nProgress: {done}/{total} done | {len(pending)} remaining\n")

                for row in pending:
                    tour_id = str(row["gyg_tour_id"])
                    title = row.get("title") or row.get("product_title") or tour_id
                    label = "Schedules" if schedules_only else "Scraping"
                    print(f"{label}: {title} ({tour_id})")

                    success = False
                    schedule_data: dict = {}
                    for attempt in range(1, MAX_RETRIES_PER_PRODUCT + 1):
                        try:
                            if schedules_only:
                                schedule_data = session.scrape_schedules_one(tour_id, catalog_row=row)
                                for i, existing in enumerate(catalog):
                                    if str(existing.get("gyg_tour_id")) == tour_id:
                                        catalog[i] = {
                                            **existing,
                                            **schedule_data,
                                            "schedules_loaded": True,
                                        }
                                        catalog[i].pop("error", None)
                                        break
                            else:
                                details = session.scrape_one(tour_id)
                                for i, existing in enumerate(catalog):
                                    if str(existing.get("gyg_tour_id")) == tour_id:
                                        catalog[i] = {**existing, **details, "details_loaded": True}
                                        catalog[i].pop("error", None)
                                        break
                            save_progress(catalog_doc, catalog)
                            if session.context:
                                save_session(session.context)
                            success = True
                            summary = (
                                schedule_data.get("schedule_summary", {})
                                if schedules_only
                                else {}
                            )
                            if schedules_only and summary:
                                times = ", ".join(summary.get("departure_times") or [])
                                prices = summary.get("retail_prices") or {}
                                print(f"  OK ({attempt}) times=[{times}] prices={prices}\n")
                            else:
                                print(f"  OK ({attempt})\n")
                            break
                        except SessionLostError as exc:
                            print(f"  Attempt {attempt}: session lost ({exc})")
                            session.restart()
                        except Exception as exc:
                            print(f"  Attempt {attempt}: {exc}")
                            if attempt >= 3 and session.page and is_login_page(session.page):
                                session.restart()
                            human_pause(3, 6)

                    if not success:
                        for i, existing in enumerate(catalog):
                            if str(existing.get("gyg_tour_id")) == tour_id:
                                if schedules_only:
                                    catalog[i]["schedules_loaded"] = False
                                else:
                                    catalog[i]["details_loaded"] = False
                                catalog[i]["error"] = "failed after retries"
                                break
                        save_progress(catalog_doc, catalog)
                        print(f"  SKIPPED after {MAX_RETRIES_PER_PRODUCT} attempts\n")

                    human_pause(2.5, 5.0)

        finally:
            session.close()

    catalog_doc, catalog = load_catalog()
    loaded = sum(1 for p in catalog if p.get("details_loaded"))
    print(f"\nFinished: {loaded}/{len(catalog)} products with full details.")
    print(f"Session saved -> {STATE_FILE}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Re-scrape all products")
    parser.add_argument("--enrich", action="store_true", help="Re-scrape all products to refresh options/inclusions")
    parser.add_argument(
        "--missing-inclusions",
        action="store_true",
        help="Re-scrape only products with empty inclusions (keeps existing catalog)",
    )
    parser.add_argument(
        "--schedules",
        action="store_true",
        help="Scrape Show schedules pricing/times for products missing schedules_loaded",
    )
    args = parser.parse_args()
    scrape_until_done(
        rescrape_all=args.all or args.enrich,
        missing_inclusions_only=args.missing_inclusions,
        schedules_only=args.schedules,
    )


if __name__ == "__main__":
    main()
