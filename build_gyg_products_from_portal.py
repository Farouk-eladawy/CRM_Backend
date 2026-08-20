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

from gyg_portal_auth import ensure_logged_in, is_login_page

ROOT = os.path.dirname(os.path.abspath(__file__))
LIST_URL = "https://supplier.getyourguide.com/products/list?limit=100"
STATE_FILE = os.path.join(ROOT, "gyg_auth_state.json")
PORTAL_CATALOG_FILE = os.path.join(ROOT, "gyg_portal_catalog.json")
PRODUCTS_FILE = os.path.join(ROOT, "gyg_products.json")
USER_DATA_DIR = os.path.join(ROOT, "gyg_browser_data")


def _slug_product_id(title: str, gyg_tour_id: str) -> str:
    """Stable unique productId for GYG API mapping. Always include tour id to avoid collisions."""
    words = re.sub(r"[^a-zA-Z0-9]+", " ", title or "").strip().upper().split()
    gyg = str(gyg_tour_id or "").strip()
    if not words:
        return f"GYG-{gyg}" if gyg else "GYG-UNKNOWN"
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
    core = re.sub(r"-+", "-", core).strip("-")[:18] or "GYG"
    return f"{core}-{gyg}" if gyg else core


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


def _euro_to_minor(value: str) -> int:
    try:
        return int(round(float(value.replace(",", "")) * 100))
    except (TypeError, ValueError):
        return 0


def _parse_schedule_panel(text: str) -> dict:
    schedule: dict = {}
    name_match = re.search(r"^(.*?)(?:Price setup|Participants|Retail price|Date range:|\nEdit\n)", text, re.S)
    if name_match:
        schedule["name"] = name_match.group(1).strip()[:120]

    price_match = re.search(
        r"Retail price\s*(.+?)(?:Minimum participants|Validity|Hide schedule|Weekday|\Z)",
        text,
        re.I | re.S,
    )
    retail: dict[str, int] = {}
    if price_match:
        for cat_match in re.finditer(r"(Infant|Child|Adult|Senior)\s*€([\d.,]+)", price_match.group(1), re.I):
            retail[cat_match.group(1).upper()] = _euro_to_minor(cat_match.group(2))
    if not retail:
        range_match = re.search(r"Pricing:\s*€([\d.,]+)\s*-\s*€([\d.,]+)", text, re.I)
        if range_match:
            retail = {
                "INFANT": _euro_to_minor(range_match.group(1)),
                "ADULT": _euro_to_minor(range_match.group(2)),
            }
    if retail:
        schedule["retail_prices"] = retail

    participants = re.search(r"Participants\s*(\d+)\s*-\s*(\d+)", text, re.I)
    if participants:
        schedule["participants_min"] = int(participants.group(1))
        schedule["participants_max"] = int(participants.group(2))

    min_booking = re.search(r"Minimum participants per booking\s*(\d+)", text, re.I)
    if min_booking:
        schedule["min_participants_per_booking"] = int(min_booking.group(1))

    validity = re.search(r"Validity\s*(.+?)(?:Hide schedule|monday|\Z)", text, re.I | re.S)
    if not validity:
        validity = re.search(r"Date range:\s*\n?\s*(.+?)(?:\nParticipants:|\nPricing:|\Z)", text, re.I | re.S)
    if validity:
        schedule["validity"] = validity.group(1).strip()[:120]

    departure_times: list[str] = []
    for day in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"):
        day_match = re.search(rf"{day}\s*(\d{{1,2}}:\d{{2}})", text, re.I)
        if day_match:
            hh, mm = day_match.group(1).split(":")
            departure_times.append(f"{int(hh):02d}:{mm}:00")
    if departure_times:
        schedule["departure_times"] = sorted(set(departure_times))
    return schedule


EXTRACT_SCHEDULES_JS = """
async () => {
  function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }
  await new Promise(r => { const f=()=>document.body?.innerText?.includes('Option ID')||document.body?.innerText?.includes('Product Id:')?r():setTimeout(f,400); f(); });
  document.querySelectorAll('iframe').forEach(f=>{ if(f.getBoundingClientRect().width>280) f.style.display='none'; });
  function parsePanel(text) {
    const result = {};
    const rp = text.match(/Retail price\\s*(.+?)(?:Minimum participants|Validity|Hide schedule|Weekday|Date range:|Pricing:|$)/is);
    if (rp) {
      const retail = {};
      for (const m of rp[1].matchAll(/(Infant|Child|Adult|Senior)\\s*€([\\d.,]+)/gi))
        retail[m[1].toUpperCase()] = Math.round(parseFloat(m[2].replace(',',''))*100);
      if (Object.keys(retail).length) result.retail_prices = retail;
    }
    if (!result.retail_prices) {
      const range = text.match(/Pricing:\\s*€([\\d.,]+)\\s*-\\s*€([\\d.,]+)/i);
      if (range) result.retail_prices = { INFANT: Math.round(parseFloat(range[1].replace(',',''))*100), ADULT: Math.round(parseFloat(range[2].replace(',',''))*100) };
    }
    const part = text.match(/Participants\\s*(\\d+)\\s*-\\s*(\\d+)/i);
    if (part) { result.participants_min = +part[1]; result.participants_max = +part[2]; }
    const times = [];
    for (const day of ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']) {
      const dm = text.match(new RegExp(day + '\\\\s*(\\\\d{1,2}:\\\\d{2})', 'i'));
      if (dm) { const [h,m]=dm[1].split(':'); times.push(String(+h).padStart(2,'0')+':'+m+':00'); }
    }
    if (times.length) result.departure_times = [...new Set(times)].sort();
    let val = text.match(/Validity\\s*(.+?)(?:Hide schedule|monday|Date range:|Pricing:|$)/is);
    if (!val) val = text.match(/Date range:\\s*\\n?\\s*(.+?)(?:\\nParticipants:|\\nPricing:|$)/is);
    if (val) result.validity = val[1].trim().slice(0,120);
    const nm = text.match(/^(.+?)(?:Price setup|Participants|Date range:|Pricing:)/s);
    if (nm && nm[1].trim().length<120) result.name = nm[1].trim();
    return result;
  }
  function parseCutoff(t){ const m=t.match(/Cut-off time:\\s*\\n?\\s*(\\d+)\\s*hours?/i); return m?+m[1]:0; }
  function getOptionId(t){ const m=t.match(/Option ID\\s*\\n\\s*(\\d+)/); return m?m[1]:''; }
  const options=[];
  let btns=[...document.querySelectorAll('button')].filter(b=>/^Show schedules$/i.test((b.innerText||'').trim()));
  for (let idx=0; idx<btns.length; idx++) {
    btns=[...document.querySelectorAll('button')].filter(b=>/^Show schedules$/i.test((b.innerText||'').trim()));
    const btn = btns[idx];
    if (!btn) continue;
    let block=btn, blockText='';
    for (let i=0;i<15;i++){ block=block.parentElement; if(!block) break; blockText=block.innerText||''; if(blockText.includes('Option ID')) break; }
    btn.scrollIntoView({block:'center'}); btn.click(); await sleep(900);
    const avail=[...document.querySelectorAll('button')].find(b=>/^Availability & Pricing$/i.test((b.innerText||'').trim()));
    if (avail) { avail.click(); await sleep(700); }
    const schedules=[];
    const seen = new Set();
    for (let a=0;a<12;a++){
      const showOne=[...document.querySelectorAll('button')].find(b=>/^Show schedule$/i.test((b.innerText||'').trim()));
      if(!showOne) break;
      showOne.scrollIntoView({block:'center'}); showOne.click(); await sleep(700);
      const hideOne=[...document.querySelectorAll('button')].find(b=>/^Hide schedule$/i.test((b.innerText||'').trim()));
      let panelText='';
      if(hideOne){ let p=hideOne.parentElement; for(let i=0;i<6&&p;i++){ panelText=p.innerText||''; if(/Participants:|Pricing:|Retail price|Monday/i.test(panelText)) break; p=p.parentElement; } }
      const parsed=parsePanel(panelText);
      const key = JSON.stringify(parsed);
      if(Object.keys(parsed).length && !seen.has(key)){ seen.add(key); schedules.push(parsed); }
      if(hideOne){ hideOne.click(); await sleep(300); }
      else break;
    }
    const hideSched=[...document.querySelectorAll('button')].find(b=>/^Hide schedules$/i.test((b.innerText||'').trim()));
    if(hideSched){ hideSched.click(); await sleep(300); }
    options.push({ option_id:getOptionId(blockText), cutoff_hours:parseCutoff(blockText), schedules });
  }
  return options;
}
"""


def extract_schedules_via_js(page) -> list[dict]:
    """Browser-DOM schedule extraction (works when Playwright locators fail)."""
    try:
        result = page.evaluate(EXTRACT_SCHEDULES_JS)
        return list(result or [])
    except Exception:
        return []


def _parse_cutoff_hours(text: str) -> int:
    match = re.search(r"Cut-off time:\s*\n?\s*(\d+)\s*hours?", text, re.I)
    if match:
        return int(match.group(1))
    return 0


def _option_block_for_button(page, button) -> str:
    try:
        block = button.locator("xpath=ancestor::div[.//text()[normalize-space()='Option ID']][1]")
        if block.count():
            return block.first.inner_text(timeout=2000)
    except Exception:
        pass
    try:
        return button.locator("xpath=ancestor::div[5]").inner_text(timeout=1500)
    except Exception:
        return ""


def _extract_option_id(option_text: str) -> str:
    match = re.search(r"Option ID\s*\n\s*(\d+)", option_text)
    return match.group(1) if match else ""


def _wizard_schedule_open(page) -> bool:
    try:
        return bool(
            page.locator('input[placeholder*="Summer"], input[placeholder*="Weekends"]').count()
            and page.get_by_role("button", name=re.compile(r"^Save and continue$", re.I)).count()
        )
    except Exception:
        return False


def _extract_wizard_schedule(page) -> dict:
    """Read schedule wizard fields (times, capacity, retail prices)."""
    schedule: dict = {}
    try:
        name_input = page.locator('input[placeholder*="Summer"], input[placeholder*="Weekends"]').first
        if name_input.count():
            schedule["name"] = (name_input.input_value(timeout=1500) or "").strip()[:120]
    except Exception:
        pass

    times: set[str] = set()
    try:
        combo_values: list[str] = []
        for combo in page.locator('[role="combobox"]').all():
            try:
                text = combo.inner_text(timeout=300).strip()
                if re.fullmatch(r"\d{2}", text):
                    combo_values.append(text)
            except Exception:
                continue
        for idx in range(0, len(combo_values) - 1, 2):
            times.add(f"{int(combo_values[idx]):02d}:{combo_values[idx + 1]}:00")
    except Exception:
        pass
    if times:
        schedule["departure_times"] = sorted(times)

    for _ in range(5):
        body = page.inner_text("body", timeout=2500)
        parsed = _parse_schedule_panel(body)
        for key, val in parsed.items():
            if val and key not in schedule:
                schedule[key] = val
        if schedule.get("retail_prices") and schedule.get("departure_times"):
            break
        try:
            nxt = page.get_by_role("button", name=re.compile(r"^Save and continue$", re.I)).first
            if not nxt.count() or not nxt.is_visible(timeout=400):
                break
            nxt.click(timeout=2000)
            time.sleep(0.7)
        except Exception:
            break
    return schedule


def _open_option_availability(page, option_id: str = "") -> None:
    dismiss_support_chat(page)
    if option_id:
        match = re.search(r"tour_id=(\d+)", page.url or "")
        if match:
            target = (
                f"https://supplier.getyourguide.com/products/details"
                f"?tour_id={match.group(1)}&optionId={option_id}"
            )
            if target not in (page.url or ""):
                page.goto(target, wait_until="domcontentloaded", timeout=60000)
                time.sleep(1.0)
    try:
        page.locator("text=Options").first.scroll_into_view_if_needed(timeout=3000)
    except Exception:
        pass
    try:
        avail = page.get_by_role("button", name=re.compile(r"^Availability & Pricing$", re.I)).first
        if avail.count() and avail.is_visible(timeout=800):
            avail.click(timeout=2000)
            time.sleep(0.5)
    except Exception:
        pass


def _schedule_panel_text(page, hide_btn) -> str:
    try:
        return hide_btn.locator("xpath=ancestor::div[3]").inner_text(timeout=2000)
    except Exception:
        try:
            return hide_btn.locator("xpath=ancestor::div[2]").inner_text(timeout=1500)
        except Exception:
            return ""


def _collect_schedules_in_open_panel(page) -> list[dict]:
    schedules: list[dict] = []
    if _wizard_schedule_open(page):
        parsed = _extract_wizard_schedule(page)
        if parsed:
            schedules.append(parsed)
        return schedules

    for _ in range(12):
        show_one = page.get_by_role("button", name=re.compile(r"^Show schedule$", re.I)).first
        try:
            if not show_one.count():
                break
            show_one.scroll_into_view_if_needed(timeout=1500)
            show_one.click(timeout=2000, force=True)
            time.sleep(0.6)
        except Exception:
            break

        hide_one = page.get_by_role("button", name=re.compile(r"^Hide schedule$", re.I)).first
        panel_text = ""
        try:
            if hide_one.count():
                panel_text = _schedule_panel_text(page, hide_one)
        except Exception:
            panel_text = ""
        if not panel_text:
            try:
                panel_text = page.inner_text("body", timeout=3000)
            except Exception:
                panel_text = ""
        parsed = _parse_schedule_panel(panel_text)
        if parsed:
            schedules.append(parsed)
        try:
            if hide_one.count():
                hide_one.click(timeout=1500)
                time.sleep(0.25)
        except Exception:
            pass

    return schedules


def extract_schedules_from_page(page, known_option_ids: list[str] | None = None) -> list[dict]:
    """Expand Show schedules / schedule rows and parse pricing + times (JS DOM clicks)."""
    via_js = extract_schedules_via_js(page)
    if known_option_ids:
        id_map = {str(o.get("option_id")): o for o in via_js if o.get("option_id")}
        return [
            id_map.get(oid) or {"option_id": oid, "cutoff_hours": 0, "schedules": []}
            for oid in known_option_ids
        ]
    return via_js


def _summarize_schedule_data(option_schedules: list[dict]) -> dict:
    departure_times: set[str] = set()
    retail_prices: dict[str, int] = {}
    participants_min = 1
    participants_max = 15
    cutoff_hours = 0
    min_booking = 1

    for option in option_schedules or []:
        if option.get("cutoff_hours"):
            cutoff_hours = max(cutoff_hours, int(option["cutoff_hours"]))
        for schedule in option.get("schedules") or []:
            for dt in schedule.get("departure_times") or []:
                departure_times.add(dt)
            for cat, price in (schedule.get("retail_prices") or {}).items():
                if cat not in retail_prices or price > retail_prices[cat]:
                    retail_prices[cat] = price
            if schedule.get("participants_min") is not None:
                participants_min = min(participants_min, int(schedule["participants_min"]))
            if schedule.get("participants_max") is not None:
                participants_max = max(participants_max, int(schedule["participants_max"]))
            if schedule.get("min_participants_per_booking") is not None:
                min_booking = max(min_booking, int(schedule["min_participants_per_booking"]))

    return {
        "departure_times": sorted(departure_times),
        "retail_prices": retail_prices,
        "participants_min": participants_min,
        "participants_max": participants_max,
        "min_participants_per_booking": min_booking,
        "cutoff_hours": cutoff_hours or 2,
    }


def scrape_product_schedules(
    page,
    tour_id: str,
    context=None,
    creds=None,
    known_option_ids: list[str] | None = None,
) -> dict:
    url = f"https://supplier.getyourguide.com/products/details?tour_id={tour_id}"
    ensure_logged_in(page, context=context, creds=creds)
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    if is_login_page(page):
        ensure_logged_in(page, context=context, creds=creds)
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_function(
        "() => document.body && document.body.innerText.includes('Product Id:')",
        timeout=45000,
    )
    time.sleep(1.2)
    dismiss_support_chat(page)
    option_schedules = extract_schedules_from_page(page, known_option_ids=known_option_ids)
    summary = _summarize_schedule_data(option_schedules)
    has_schedules = any(opt.get("schedules") for opt in option_schedules)
    return {
        "gyg_tour_id": tour_id,
        "option_schedules": option_schedules,
        "schedule_summary": summary,
        "schedules_loaded": has_schedules,
        "schedules_scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def scrape_product_details(page, tour_id: str, context=None, creds=None) -> dict:
    url = f"https://supplier.getyourguide.com/products/details?tour_id={tour_id}"
    ensure_logged_in(page, context=context, creds=creds)
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    if is_login_page(page):
        ensure_logged_in(page, context=context, creds=creds)
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
    if not pickup:
        title_for_pickup = ""
        for selector in ("h1", "h3"):
            loc = page.locator(selector)
            for i in range(min(loc.count(), 3)):
                try:
                    text = loc.nth(i).inner_text(timeout=1500).strip()
                    if text and text not in {"Products", "Supply Partner"} and len(text) > 10:
                        title_for_pickup = text
                        break
                except Exception:
                    continue
            if title_for_pickup:
                break
        if not title_for_pickup:
            m = re.search(r"Product Reference Code:\s*\S+\s*\n(.+?)(?:\n|$)", body_text)
            if m:
                title_for_pickup = m.group(1).strip()
        pickup = _city_from_title(title_for_pickup, "")

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

    schedule_summary = details.get("schedule_summary") or {}
    departure_times = list(schedule_summary.get("departure_times") or [])
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

    retail = schedule_summary.get("retail_prices") or {}
    participants_min = int(schedule_summary.get("participants_min") or 1)
    participants_max = int(schedule_summary.get("participants_max") or 15)
    cutoff_hours = int(schedule_summary.get("cutoff_hours") or 2)
    min_ticket = int(schedule_summary.get("min_participants_per_booking") or 1)
    daily_capacity = min(max(participants_max, 15), 500)

    categories = {
        "ADULT": {
            "enabled": True,
            "retail_minor": int(retail.get("ADULT") or 10000),
            "min_ticket_amount": min_ticket,
            "max_ticket_amount": daily_capacity,
            "age_from": 12,
            "age_to": 99,
        },
        "CHILD": {
            "enabled": "CHILD" in retail or not retail,
            "retail_minor": int(retail.get("CHILD") or 7500),
            "min_ticket_amount": 0,
            "max_ticket_amount": daily_capacity,
            "age_from": 4,
            "age_to": 11,
        },
        "INFANT": {
            "enabled": "INFANT" in retail or not retail,
            "retail_minor": int(retail.get("INFANT") or 0),
            "min_ticket_amount": 0,
            "max_ticket_amount": min(5, daily_capacity),
            "age_from": 0,
            "age_to": 3,
        },
    }
    if retail.get("SENIOR"):
        categories["SENIOR"] = {
            "enabled": True,
            "retail_minor": int(retail["SENIOR"]),
            "min_ticket_amount": min_ticket,
            "max_ticket_amount": daily_capacity,
            "age_from": 65,
            "age_to": 99,
        }

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
        "option_schedules": details.get("option_schedules") or [],
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
        "daily_capacity": daily_capacity,
        "participants_min": participants_min,
        "participants_max": participants_max,
        "cutoff_hours": cutoff_hours,
        "cutoff_seconds": cutoff_hours * 3600,
        "closed_weekdays": [],
        "blockout_dates": [],
        "departure_times": departure_times,
        "categories": categories,
        "details_loaded": True,
        "schedules_loaded": bool(details.get("schedules_loaded")),
        "scraped_at": details.get("scraped_at"),
        "schedules_scraped_at": details.get("schedules_scraped_at"),
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
