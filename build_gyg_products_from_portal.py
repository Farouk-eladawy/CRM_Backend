"""Build gyg_products.json + gyg_portal_catalog.json from supplier.getyourguide.com.

Requires an authenticated supplier session (gyg_auth_state.json or manual login in headed browser).
Reuses extraction logic from scrape_gyg_supplier.py.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.abspath(__file__))
LIST_URL = "https://supplier.getyourguide.com/products/list?limit=100"
STATE_FILE = os.path.join(ROOT, "gyg_auth_state.json")
PORTAL_CATALOG_FILE = os.path.join(ROOT, "gyg_portal_catalog.json")
PRODUCTS_FILE = os.path.join(ROOT, "gyg_products.json")
USER_DATA_DIR = os.path.join(ROOT, "gyg_browser_data")


def _slug_product_id(title: str, gyg_tour_id: str) -> str:
    words = re.sub(r"[^a-zA-Z0-9]+", " ", title or "").strip().upper().split()
    if not words:
        return f"GYG-{gyg_tour_id}"
    if words[0] in {"FROM", "HURGHADA", "SHARM", "CAIRO", "LUXOR", "MARSA"} and len(words) > 1:
        prefix = words[1][:4] if words[0] == "FROM" else words[0][:3]
    else:
        prefix = words[0][:4]
    dest = ""
    lower = (title or "").lower()
    if "hurghada" in lower:
        dest = "HRG"
    elif "sharm" in lower or "dahab" in lower:
        dest = "SSH"
    elif "cairo" in lower or "giza" in lower or "pyramid" in lower:
        dest = "CAI"
    elif "luxor" in lower:
        dest = "LXR"
    elif "marsa" in lower:
        dest = "MRM"
    elif "alexandria" in lower:
        dest = "ALX"
    core = prefix + (f"-{dest}" if dest else "")
    return re.sub(r"-+", "-", core).strip("-")[:24] or f"GYG-{gyg_tour_id}"


def _city_from_title(title: str, public_url: str = "") -> str:
    text = f"{title} {public_url}".lower()
    if "hurghada" in text or "makadi" in text or "el gouna" in text:
        return "Hurghada"
    if "sharm" in text or "dahab" in text or "ras mohamed" in text:
        return "Sharm"
    if "luxor" in text:
        return "Luxor"
    if "cairo" in text or "giza" in text or "pyramid" in text:
        return "Cairo"
    if "marsa alam" in text:
        return "Marsa Alam"
    if "alexandria" in text:
        return "Alexandria"
    if "fayoum" in text or "fayum" in text:
        return "Fayoum"
    return ""


def _tour_id_from_public_url(url: str) -> str:
    m = re.search(r"-t(\d+)/?", url or "", re.I)
    return m.group(1) if m else ""


def scrape_product_list(page) -> list[dict]:
    page.goto(LIST_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector("table tbody tr", timeout=30000)
    time.sleep(2)
    rows = page.locator("table tbody tr")
    out = []
    for i in range(rows.count()):
        row = rows.nth(i)
        cells = row.locator("td")
        ref_text = ""
        for j in range(cells.count()):
            txt = cells.nth(j).inner_text(timeout=1000).strip()
            if re.match(r"T-\d+", txt):
                ref_text = txt
                break
        title = row.locator("td a").first.inner_text(timeout=2000).strip()
        preview = row.locator("a[href*='getyourguide.com']").first
        public_url = preview.get_attribute("href") if preview.count() else ""
        if public_url:
            public_url = public_url.split("?")[0]
        gyg_tour_id = _tour_id_from_public_url(public_url) or (re.search(r"T-(\d+)", ref_text or "") or ["", ""])[1]
        rating = "Not rated"
        cell0 = cells.first.inner_text(timeout=1000)
        m = re.search(r"(\d\.\d of 5)", cell0)
        if m:
            rating = m.group(1)
        out.append({
            "title": title,
            "reference": ref_text,
            "gyg_tour_id": gyg_tour_id,
            "rating": rating,
            "status": "Bookable",
            "public_url": public_url,
            "supplier_url": f"https://supplier.getyourguide.com/products/details?tour_id={gyg_tour_id}",
        })
    return out


def dismiss_support_chat(page) -> None:
    """Hide supplier portal support chat iframe that blocks See-all clicks."""
    try:
        page.evaluate(
            """
            () => {
                document.querySelectorAll('iframe').forEach((iframe) => {
                    const r = iframe.getBoundingClientRect();
                    const src = (iframe.src || '').toLowerCase();
                    const title = (iframe.title || '').toLowerCase();
                    if (
                        (r.width >= 280 && r.height >= 350 && r.right > window.innerWidth - 450) ||
                        src.includes('support') || src.includes('chat') || src.includes('zendesk') ||
                        title.includes('support') || title.includes('chat')
                    ) {
                        iframe.style.setProperty('display', 'none', 'important');
                        iframe.style.setProperty('visibility', 'hidden', 'important');
                        iframe.style.setProperty('pointer-events', 'none', 'important');
                    }
                });
                document.querySelectorAll(
                    '[class*="launcher"], [id*="launcher"], [class*="ChatWidget"], [id*="chat-widget"]'
                ).forEach((el) => {
                    el.style.setProperty('display', 'none', 'important');
                });
            }
            """
        )
    except Exception:
        pass


def _click_see_all(page, pattern: str) -> None:
    dismiss_support_chat(page)
    regex = re.compile(pattern, re.I)
    for el in page.get_by_text(regex).all():
        try:
            if not el.is_visible():
                continue
            el.scroll_into_view_if_needed(timeout=1500)
            dismiss_support_chat(page)
            clicked = False
            for xpath in ("ancestor::button[1]", "ancestor::a[1]"):
                try:
                    target = el.locator(f"xpath={xpath}")
                    if target.count() and target.first.is_visible():
                        target.first.click(timeout=2000)
                        clicked = True
                        break
                except Exception:
                    pass
            if not clicked:
                el.click(timeout=2000)
            time.sleep(0.35)
        except Exception:
            pass


def expand_sections(page) -> None:
    """Expand accordions, See all/more buttons, and option panels."""
    dismiss_support_chat(page)
    try:
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(0.3)
    except Exception:
        pass

    for _ in range(2):
        dismiss_support_chat(page)
        for pattern in (
            r"See all \d+ inclusions",
            r"See all \d+ exclusions",
            r"See all \d+ highlights",
            r"See all \d+",
            r"^See more",
        ):
            _click_see_all(page, pattern)

        for btn in page.locator("button[aria-expanded='false']").all():
            try:
                if btn.is_visible():
                    dismiss_support_chat(page)
                    btn.scroll_into_view_if_needed(timeout=800)
                    btn.click(timeout=1000)
                    time.sleep(0.2)
            except Exception:
                pass

        for sp in page.locator("span.p-button-label").all():
            try:
                if sp.is_visible() and re.search(r"see (all|more)", sp.inner_text(timeout=300), re.I):
                    dismiss_support_chat(page)
                    sp.scroll_into_view_if_needed(timeout=800)
                    sp.click(timeout=1000)
                    time.sleep(0.2)
            except Exception:
                try:
                    sp.locator("..").click(timeout=800)
                except Exception:
                    pass

        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            time.sleep(0.3)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(0.3)
        except Exception:
            pass


def _clean_list_item(text: str) -> str:
    return re.sub(r"^[•\-✘]\s*", "", (text or "").strip())


def pick_list_from_page(page, testid: str, label: str) -> list[str]:
    items: list[str] = []
    for el in page.locator(f"[data-testid='{testid}'] li").all():
        txt = _clean_list_item(el.inner_text(timeout=500))
        if txt:
            items.append(txt)
    if items:
        return items
    for el in page.locator(f"xpath=//span[contains(text(), '{label}')]/following-sibling::*//li").all():
        txt = _clean_list_item(el.inner_text(timeout=500))
        if txt:
            items.append(txt)
    return items


def extract_options_from_page(page) -> list[dict]:
    options: list[dict] = []
    seen: set[str] = set()
    for label in page.get_by_text("Option ID", exact=True).all():
        try:
            card = label.locator("..").locator("..")
            card_text = card.inner_text(timeout=1500)
            option: dict[str, str] = {}
            lines = [ln.strip() for ln in card_text.split("\n")]
            for idx, line in enumerate(lines):
                if line == "Title" and idx + 1 < len(lines):
                    title = lines[idx + 1].strip()
                    if title.startswith("Option ") or len(title) <= 100:
                        option["title"] = title.split("\n")[0][:120]
                elif line == "Reference code" and idx + 1 < len(lines):
                    option["reference_code"] = lines[idx + 1].strip()
                elif line == "Option ID" and idx + 1 < len(lines):
                    option["option_id"] = lines[idx + 1].strip()
                elif line == "Status" and idx + 1 < len(lines):
                    option["status"] = lines[idx + 1].strip()
                elif line == "Type" and idx + 1 < len(lines):
                    option["type"] = lines[idx + 1].strip()
            opt_id = option.get("option_id", "")
            if opt_id and opt_id not in seen:
                seen.add(opt_id)
                options.append(option)
        except Exception:
            continue
    return options


def _parse_list_section(body_text: str, header: str, stop_headers: tuple[str, ...]) -> list[str]:
    lines = body_text.split("\n")
    stop_set = {h.lower() for h in stop_headers}
    header_lower = header.lower()
    in_section = False
    skip = {
        "edit",
        "see less",
        "see all",
        "see more",
        "inclusions & exclusions",
        header_lower,
    }
    items: list[str] = []
    for line in lines:
        stripped = line.strip()
        low = stripped.lower()
        if not in_section:
            if low == header_lower:
                in_section = True
            continue
        if low in stop_set:
            break
        if low.startswith("see all ") or low.startswith("see less"):
            continue
        txt = _clean_list_item(stripped)
        if not txt or low in skip or len(txt) < 3:
            continue
        items.append(txt)
    return items


def _parse_options_from_body(body_text: str) -> list[dict]:
    options: list[dict] = []
    pattern = re.compile(
        r"Title\s*\n(.+?)\s*\nReference code\s*\n(.+?)\s*\nOption ID\s*\n(\d+)\s*\nStatus\s*\n(Active|Deactivated|Bookable)",
        re.DOTALL,
    )
    for match in pattern.finditer(body_text):
        title = match.group(1).strip().split("\n")[0][:120]
        if "Short description" in title or len(match.group(1)) > 120:
            continue
        options.append({
            "title": title,
            "reference_code": match.group(2).strip().split("\n")[0],
            "option_id": match.group(3).strip(),
            "status": match.group(4).strip(),
        })
    return options


def scrape_product_details(page, tour_id: str) -> dict:
    url = f"https://supplier.getyourguide.com/products/details?tour_id={tour_id}"
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_function(
        "() => document.body && document.body.innerText.includes('Product Id:')",
        timeout=45000,
    )
    time.sleep(1.5)
    dismiss_support_chat(page)
    expand_sections(page)
    time.sleep(0.8)
    dismiss_support_chat(page)
    expand_sections(page)
    time.sleep(0.5)

    body_text = page.inner_text("body", timeout=10000)
    if "History" in body_text:
        body_text = body_text.split("History\nDate")[0].strip()

    def pick_testid(testid: str) -> str:
        loc = page.locator(f"[data-testid='{testid}']")
        try:
            return loc.first.inner_text(timeout=1500).strip()
        except Exception:
            return ""

    def pick_list(testid: str, label: str = "") -> list[str]:
        label = label or testid.replace("pdp-details-main-information-", "").title()
        return pick_list_from_page(page, testid, label)

    product_id = ""
    m = re.search(r"Product Id:\s*(\d+)", body_text)
    if m:
        product_id = m.group(1)
    ref_code = ""
    m = re.search(r"Product Reference Code:\s*(\S+)", body_text)
    if m:
        ref_code = m.group(1)

    short_desc = pick_testid("pdp-details-main-information-short-desc")
    full_desc = pick_testid("pdp-details-main-information-full-desc")
    highlights = pick_list("pdp-details-main-information-highlights")
    body_inclusions = _parse_list_section(
        body_text, "Inclusions", ("Exclusions", "Important information", "Itinerary", "Options")
    )
    body_exclusions = _parse_list_section(
        body_text, "Exclusions", ("Important information", "Itinerary", "Options", "Know before you go")
    )
    inclusions = pick_list("pdp-details-main-information-inclusions", "Inclusions")
    exclusions = pick_list("pdp-details-main-information-exclusions", "Exclusions")
    if len(body_inclusions) >= len(inclusions):
        inclusions = body_inclusions
    if len(body_exclusions) >= len(exclusions):
        exclusions = body_exclusions
    inc_lower = {item.lower() for item in inclusions}
    exclusions = [item for item in exclusions if item.lower() not in inc_lower]

    if not short_desc:
        m = re.search(r"Short description\s*\n+(.+?)(?=\n+Full description)", body_text, re.DOTALL)
        if m:
            short_desc = m.group(1).strip()
    if not full_desc:
        m = re.search(r"Full description\s*\n+(.+?)(?=\n+See less|\n+Highlights)", body_text, re.DOTALL)
        if m:
            full_desc = re.sub(r"\nSee less.*$", "", m.group(1).strip(), flags=re.DOTALL)

    options = extract_options_from_page(page)
    if not options:
        options = _parse_options_from_body(body_text)

    pickup = ""
    m = re.search(r"Pickup location:\s*\n(.+?)(?:\n|$)", body_text)
    if m:
        pickup = m.group(1).strip()
    if not pickup:
        try:
            pickup = page.locator("xpath=//div[contains(text(),'Pickup location')]/following-sibling::*").first.inner_text(timeout=1000).strip()
        except Exception:
            pass

    transportation = ""
    m = re.search(r"Transportation\s*\n+(.+?)(?=\n+Refund policy)", body_text, re.DOTALL)
    if m:
        transportation = m.group(1).replace("\n", ", ").strip()
    transportation = re.sub(r"^Edit,\s*", "", transportation)

    title = ""
    for selector in ("h1", "h3"):
        loc = page.locator(selector)
        for i in range(min(loc.count(), 3)):
            try:
                text = loc.nth(i).inner_text(timeout=1500).strip()
                if text and text not in {"Products", "Supply Partner"} and len(text) > 10:
                    title = text
                    break
            except Exception:
                continue
        if title:
            break
    if not title:
        m = re.search(r"Product Reference Code:\s*\S+\s*\n(.+?)(?:\n|$)", body_text)
        if m:
            title = m.group(1).strip()

    return {
        "gyg_tour_id": product_id or tour_id,
        "reference_code": ref_code,
        "product_title": title,
        "short_description": short_desc,
        "product_description": full_desc,
        "highlights": highlights,
        "inclusions": inclusions,
        "exclusions": exclusions,
        "pickup_location": pickup,
        "transportation": transportation,
        "options": options,
        "details_loaded": True,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def build_api_product(row: dict, details: dict) -> dict:
    gyg_id = str(details.get("gyg_tour_id") or row.get("gyg_tour_id") or "")
    title = details.get("product_title") or row.get("title") or ""
    city = _city_from_title(title, row.get("public_url") or "")
    product_id = _slug_product_id(title, gyg_id)
    departure_times = []
    for opt in details.get("options") or []:
        # schedules are on a separate modal; default single morning slot unless scraped later
        pass
    if not departure_times:
        lower = title.lower()
        if "luxor" in lower and "hurghada" in lower:
            departure_times = ["03:00:00", "03:30:00"]
        elif "cairo" in lower and ("plane" in lower or "flight" in lower):
            departure_times = ["04:00:00"]
        elif "cairo" in lower and "bus" in lower:
            departure_times = ["00:25:00", "00:40:00"]
        else:
            departure_times = ["08:00:00"]

    return {
        "product_id": product_id,
        "gyg_tour_id": gyg_id,
        "reference_code": details.get("reference_code") or row.get("reference") or "",
        "product_title": title,
        "short_description": details.get("short_description") or "",
        "product_description": details.get("product_description") or "",
        "highlights": details.get("highlights") or [],
        "inclusions": details.get("inclusions") or [],
        "exclusions": details.get("exclusions") or [],
        "pickup_location": details.get("pickup_location") or "",
        "transportation": details.get("transportation") or "",
        "options_portal": details.get("options") or [],
        "live": str(row.get("status") or "").lower() == "bookable",
        "api_connected": False,
        "pilot": gyg_id in {"1191624", "1303745"},
        "destination_name": city,
        "city": city,
        "location": f"{city}, Egypt" if city else "Egypt",
        "country": "EGY",
        "rating": row.get("rating") or "Not rated",
        "public_url": row.get("public_url") or "",
        "supplier_url": row.get("supplier_url") or f"https://supplier.getyourguide.com/products/details?tour_id={gyg_id}",
        "daily_capacity": 15,
        "participants_min": 1,
        "participants_max": 15,
        "cutoff_hours": 2,
        "cutoff_seconds": 7200,
        "closed_weekdays": [],
        "blockout_dates": [],
        "departure_times": departure_times,
        "categories": {
            "ADULT": {"enabled": True, "retail_minor": 10000, "min_ticket_amount": 1, "max_ticket_amount": 15, "age_from": 12, "age_to": 99},
            "CHILD": {"enabled": True, "retail_minor": 7500, "min_ticket_amount": 0, "max_ticket_amount": 15, "age_from": 4, "age_to": 11},
            "INFANT": {"enabled": True, "retail_minor": 0, "min_ticket_amount": 0, "max_ticket_amount": 5, "age_from": 0, "age_to": 3},
        },
        "details_loaded": True,
        "scraped_at": details.get("scraped_at"),
    }


def main() -> None:
    catalog: list[dict] = []
    api_products: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=False)
        context_kwargs = {"viewport": {"width": 1400, "height": 900}}
        if os.path.isfile(STATE_FILE):
            context_kwargs["storage_state"] = STATE_FILE
        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        page.goto(LIST_URL, wait_until="domcontentloaded", timeout=60000)

        if "login" in page.url.lower():
            print("Session expired. Waiting up to 120s for manual login in the opened browser...")
            for _ in range(60):
                if "login" not in page.url.lower():
                    break
                time.sleep(2)
            if "login" in page.url.lower():
                raise RuntimeError("Login required: open supplier.getyourguide.com and sign in, then rerun.")

        listing = scrape_product_list(page)
        print(f"Found {len(listing)} bookable products on portal list.")

        for idx, row in enumerate(listing, start=1):
            tour_id = row.get("gyg_tour_id") or _tour_id_from_public_url(row.get("public_url") or "")
            if not tour_id:
                print(f"Skip row without tour id: {row.get('title')}")
                continue
            print(f"[{idx}/{len(listing)}] Details: {row.get('title')} ({tour_id})")
            try:
                details = scrape_product_details(page, tour_id)
                merged = {**row, **details}
                catalog.append(merged)
                api_products.append(build_api_product(row, details))
            except Exception as exc:
                print(f"  FAILED: {exc}")
                catalog.append({**row, "details_loaded": False, "error": str(exc)})

            if idx % 3 == 0:
                _save_outputs(catalog, api_products)

            time.sleep(1.2)

        context.storage_state(path=STATE_FILE)
        context.close()
        browser.close()

    _save_outputs(catalog, api_products)
    print(f"Saved {len(catalog)} portal records -> {PORTAL_CATALOG_FILE}")
    print(f"Saved {len(api_products)} API products -> {PRODUCTS_FILE}")


def _save_outputs(catalog: list[dict], api_products: list[dict]) -> None:
    with open(PORTAL_CATALOG_FILE, "w", encoding="utf-8") as handle:
        json.dump({
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "source": LIST_URL,
            "count": len(catalog),
            "products": catalog,
        }, handle, ensure_ascii=False, indent=2)

    with open(PRODUCTS_FILE, "w", encoding="utf-8") as handle:
        json.dump({
            "supplier_id": "fts-travels",
            "supplier_name": "FTS Travels",
            "currency": "EUR",
            "source": {
                "portal_url": LIST_URL,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "catalog_count": len(api_products),
            },
            "products": api_products,
        }, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
