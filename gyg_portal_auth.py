"""GYG supplier portal login helpers — Edge profile + auto-login + 2FA."""

from __future__ import annotations

import json
import os
import random
import re
import time
from typing import Optional

import pyotp
from playwright.sync_api import BrowserContext, Page, Playwright, TimeoutError as PlaywrightTimeout

ROOT = os.path.dirname(os.path.abspath(__file__))
USER_DATA_DIR = os.path.join(ROOT, "gyg_browser_data_edge")
STATE_FILE = os.path.join(ROOT, "gyg_auth_state.json")
CREDS_FILE = os.path.join(ROOT, "gyg_portal_credentials.json")
LOGIN_URL = "https://supplier.getyourguide.com/auth/login"
LIST_URL = "https://supplier.getyourguide.com/products/list?limit=100"

EMAIL_SELECTORS = (
    "input[type='email']",
    "input[name='email']",
    "input[autocomplete='username']",
    "input[placeholder*='email' i]",
    "input[id*='email' i]",
    "label:has-text('Email') + input",
    "label:has-text('Email') ~ input",
)

PASSWORD_SELECTORS = (
    "input[type='password']",
    "input[name='password']",
    "input[autocomplete='current-password']",
    "input[placeholder*='password' i]",
)

LOGIN_BUTTON_SELECTORS = (
    "button:has-text('Log in')",
    "button:has-text('Log In')",
    "button[type='submit']",
    "input[type='submit']",
)


def _strip_env(val: str) -> str:
    return val.strip().strip('"')


def _load_credentials() -> dict[str, str]:
    creds: dict[str, str] = {}
    env_map = (
        ("email", ("GYG_EMAIL_1", "GYG_PORTAL_EMAIL")),
        ("password", ("GYG_PASSWORD_1", "GYG_PORTAL_PASSWORD")),
        ("totp_secret", ("GYG_2FA_SECRET_1", "GYG_PORTAL_TOTP_SECRET")),
    )
    for key, env_keys in env_map:
        for env_key in env_keys:
            val = os.environ.get(env_key, "")
            if val:
                creds[key] = _strip_env(val)
                break

    if os.path.isfile(CREDS_FILE):
        with open(CREDS_FILE, encoding="utf-8") as handle:
            file_creds = json.load(handle)
        for key in ("email", "password", "totp_secret"):
            if not creds.get(key) and file_creds.get(key):
                creds[key] = _strip_env(str(file_creds[key]))
    return creds


def is_login_page(page: Page) -> bool:
    url = (page.url or "").lower()
    if any(token in url for token in ("login", "/auth/", "signin")):
        return True
    try:
        body = page.inner_text("body", timeout=2500).lower()
    except Exception:
        return True
    markers = (
        "log in to the supplier portal",
        "log in again to continue",
        "there was an error with your session",
        "enter your email",
    )
    return any(m in body for m in markers)


def _first_visible(page: Page, selectors: tuple[str, ...]):
    for selector in selectors:
        loc = page.locator(selector).first
        try:
            if loc.count() and loc.is_visible(timeout=800):
                return loc
        except Exception:
            continue
    return None


def _fill_login_form(page: Page, email: str, password: str) -> None:
    page.wait_for_load_state("domcontentloaded", timeout=30000)
    time.sleep(1.0)

    email_input = _first_visible(page, EMAIL_SELECTORS)
    if not email_input:
        raise RuntimeError("Email field not found on login page")

    password_input = _first_visible(page, PASSWORD_SELECTORS)
    if not password_input:
        raise RuntimeError("Password field not found on login page")

    email_input.click()
    email_input.fill("")
    email_input.fill(email)
    time.sleep(random.uniform(0.3, 0.7))

    password_input.click()
    password_input.fill("")
    password_input.fill(password)
    time.sleep(random.uniform(0.3, 0.7))

    login_btn = _first_visible(page, LOGIN_BUTTON_SELECTORS)
    if login_btn:
        login_btn.click()
    else:
        page.keyboard.press("Enter")


def _submit_2fa(page: Page, totp_secret: str) -> None:
    code = pyotp.TOTP(totp_secret.replace(" ", "").upper()).now()
    print("2FA code generated — submitting TOTP...")
    page.wait_for_selector("input", timeout=20000)

    code_input = page.locator(
        "input[name='code'], input[name='otp'], input[placeholder*='code' i], "
        "input[autocomplete='one-time-code'], input[type='tel'], input[inputmode='numeric']"
    ).first
    if code_input.is_visible():
        code_input.fill(code)
        try:
            page.click(
                "button[type='submit'], button:has-text('Verify'), button:has-text('Confirm'), button:has-text('Log in')",
                timeout=3000,
            )
        except Exception:
            page.keyboard.press("Enter")
        return

    inputs = [
        i for i in page.locator("input[type='text'], input[type='tel'], input[inputmode='numeric']").all()
        if i.is_visible()
    ]
    if len(inputs) == 6:
        for i, digit in enumerate(code):
            inputs[i].fill(digit)
        page.keyboard.press("Enter")
    elif inputs:
        inputs[0].fill(code)
        page.keyboard.press("Enter")
    else:
        print("Could not find 2FA field — enter code manually if prompted.")


def auto_login(page: Page, creds: dict[str, str]) -> bool:
    email = creds.get("email", "")
    password = creds.get("password", "")
    if not email or not password:
        print("ERROR: Missing email or password in credentials.")
        return False

    masked = email.split("@")[0][:3] + "***@" + email.split("@")[-1] if "@" in email else "***"
    print(f"Auto-login as {masked} ...")

    try:
        if not is_login_page(page):
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
        else:
            # stay on current login redirect URL
            if "/auth/login" not in page.url.lower():
                page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)

        if not is_login_page(page):
            print("Already logged in.")
            return True

        _fill_login_form(page, email, password)
        time.sleep(random.uniform(3.0, 5.0))

        if creds.get("totp_secret") and is_login_page(page):
            body = page.inner_text("body", timeout=3000).lower()
            if any(k in body for k in ("verification", "authenticator", "two-factor", "2fa", "security code")):
                _submit_2fa(page, creds["totp_secret"])
                time.sleep(random.uniform(3.0, 5.0))

        for _ in range(40):
            if not is_login_page(page):
                print("Auto-login succeeded.")
                page.goto(LIST_URL, wait_until="domcontentloaded", timeout=60000)
                return True
            time.sleep(2)

        print("Auto-login failed: still on login page after submit.")
    except PlaywrightTimeout as exc:
        print(f"Auto-login timeout: {exc}")
    except Exception as exc:
        print(f"Auto-login error: {exc}")
    return False


def wait_for_manual_login(page: Page, timeout_sec: int = 600) -> None:
    print("\n>>> Auto-login failed — sign in manually in the browser (max 10 min) <<<\n")
    for remaining in range(timeout_sec, 0, -5):
        if not is_login_page(page):
            print("Login detected.")
            time.sleep(2)
            return
        mins, secs = divmod(remaining, 60)
        print(f"\rWaiting for login... {mins:02d}:{secs:02d} ", end="", flush=True)
        time.sleep(5)
    raise RuntimeError("Login timeout")


def ensure_session(page: Page, context: BrowserContext, creds: Optional[dict[str, str]] = None) -> None:
    creds = creds if creds is not None else _load_credentials()
    if not creds.get("email"):
        raise RuntimeError(
            "No GYG credentials found. Set gyg_portal_credentials.json or env GYG_EMAIL_1 / GYG_PASSWORD_1 / GYG_2FA_SECRET_1"
        )

    page.goto(LIST_URL, wait_until="domcontentloaded", timeout=90000)
    if not is_login_page(page):
        print("Session OK — already logged in.")
        context.storage_state(path=STATE_FILE)
        return

    print("Login page detected — starting auto-login...")
    if auto_login(page, creds) and not is_login_page(page):
        context.storage_state(path=STATE_FILE)
        print("Session saved after login.")
        return

    wait_for_manual_login(page)
    context.storage_state(path=STATE_FILE)


def launch_browser_context(p: Playwright) -> BrowserContext:
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    print(f"Browser profile: {USER_DATA_DIR}")
    print("Close any other GYG supplier tabs before scraping.\n")
    return p.chromium.launch_persistent_context(
        USER_DATA_DIR,
        channel="msedge",
        headless=False,
        viewport={"width": 1400, "height": 900},
        locale="en-US",
        timezone_id="Africa/Cairo",
        args=["--disable-blink-features=AutomationControlled"],
    )


launch_firefox_context = launch_browser_context


def human_pause(min_sec: float = 2.0, max_sec: float = 4.5) -> None:
    time.sleep(random.uniform(min_sec, max_sec))


def save_session(context: BrowserContext) -> None:
    try:
        context.storage_state(path=STATE_FILE)
    except Exception as exc:
        print(f"Could not save session: {exc}")
