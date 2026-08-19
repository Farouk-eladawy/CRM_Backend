"""Quick test: open Edge, auto-login to GYG supplier portal."""

from __future__ import annotations

from playwright.sync_api import sync_playwright

from gyg_portal_auth import (
    LIST_URL,
    _load_credentials,
    ensure_session,
    is_authenticated,
    launch_firefox_context,
)


def main() -> None:
    creds = _load_credentials()
    if not creds.get("email"):
        raise SystemExit("Missing gyg_portal_credentials.json")

    with sync_playwright() as p:
        context = launch_firefox_context(p)
        page = context.pages[0] if context.pages else context.new_page()
        ensure_session(page, context, creds)
        page.goto(LIST_URL, wait_until="domcontentloaded", timeout=60000)
        ok = is_authenticated(page)
        print(f"Authenticated: {ok}")
        print(f"URL: {page.url}")
        input("\nPress Enter to close browser...")
        context.close()


if __name__ == "__main__":
    main()
