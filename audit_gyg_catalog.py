import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(ROOT, "gyg_portal_catalog.json"), encoding="utf-8") as f:
    cat = json.load(f)
with open(os.path.join(ROOT, "gyg_products.json"), encoding="utf-8") as f:
    api = json.load(f)

issues = []
for p in cat["products"]:
    tid = str(p.get("gyg_tour_id", ""))
    flags = []
    if not p.get("details_loaded"):
        flags.append("NOT_LOADED")
    if not (p.get("short_description") or "").strip():
        flags.append("no_short_desc")
    if not (p.get("product_description") or "").strip():
        flags.append("no_full_desc")
    if len(p.get("highlights") or []) == 0:
        flags.append("no_highlights")
    if not (p.get("pickup_location") or "").strip():
        flags.append("no_pickup")
    if not (p.get("transportation") or "").strip():
        flags.append("no_transport")
    if len(p.get("inclusions") or []) == 0:
        flags.append("no_inclusions")
    if len(p.get("exclusions") or []) == 0:
        flags.append("no_exclusions")
    opts = p.get("options") or []
    if not opts:
        flags.append("no_options")
    else:
        for o in opts:
            t = o.get("title", "")
            if len(t) > 120 or "Short description" in t:
                flags.append("options_corrupt")
            break
    if (p.get("product_description") or "").rstrip().endswith("See more"):
        flags.append("desc_truncated")
    issues.append(
        {
            "id": tid,
            "title": (p.get("product_title") or p.get("title", ""))[:55],
            "flags": flags,
            "hl": len(p.get("highlights") or []),
            "opts": len(opts),
            "inc": len(p.get("inclusions") or []),
        }
    )

loaded = sum(1 for p in cat["products"] if p.get("details_loaded"))
print(f"CATALOG: {loaded}/{len(cat['products'])} loaded")
print(f"API: {len(api.get('products', []))} products")
print()
for r in issues:
    core_ok = not any(
        f in r["flags"]
        for f in ("NOT_LOADED", "no_short_desc", "no_full_desc", "no_highlights", "options_corrupt", "desc_truncated")
    )
    status = "CORE_OK" if core_ok else "ISSUES"
    extra = [f for f in r["flags"] if f not in ("no_inclusions", "no_exclusions", "no_options", "no_pickup")]
    print(f"{r['id']} | {status} | hl={r['hl']} opts={r['opts']} inc={r.get('inc',0)} | {', '.join(r['flags']) or 'complete'}")
    print(f"   {r['title']}")
