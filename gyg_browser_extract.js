// Run via browser CDP Runtime.evaluate on each product details page
async function extractGygProductDetails() {
  await new Promise((r) => setTimeout(r, 2500));

  document.querySelectorAll('button[aria-expanded="false"]').forEach((b) => {
    try {
      if (b.offsetParent !== null) b.click();
    } catch (_) {}
  });
  [...document.querySelectorAll("button, a, span, div")].forEach((el) => {
    const t = (el.innerText || "").trim();
    if (/^See (more|all)/i.test(t) || /See all \d+/i.test(t)) {
      try {
        if (el.offsetParent !== null) el.click();
      } catch (_) {}
    }
  });
  await new Promise((r) => setTimeout(r, 900));

  let bodyText = document.body.innerText || "";
  if (bodyText.includes("History")) {
    bodyText = bodyText.split("History\nDate")[0].trim();
  }

  const pick = (testid) => {
    const el = document.querySelector(`[data-testid="${testid}"]`);
    return el ? el.innerText.trim() : "";
  };
  const pickList = (testid) =>
    [...document.querySelectorAll(`[data-testid="${testid}"] li`)]
      .map((li) => li.innerText.trim().replace(/^[•\-]\s*/, ""))
      .filter(Boolean);

  const productIdMatch = bodyText.match(/Product Id:\s*(\d+)/);
  const refMatch = bodyText.match(/Product Reference Code:\s*(\S+)/);

  let shortDesc = pick("pdp-details-main-information-short-desc");
  let fullDesc = pick("pdp-details-main-information-full-desc");
  if (!shortDesc) {
    const m = bodyText.match(/Short description\s*\n+([\s\S]+?)(?=\n+Full description)/);
    if (m) shortDesc = m[1].trim();
  }
  if (!fullDesc) {
    const m = bodyText.match(/Full description\s*\n+([\s\S]+?)(?=\n+See less|\n+Highlights)/);
    if (m) fullDesc = m[1].replace(/\nSee less[\s\S]*$/, "").trim();
  }

  const options = [];
  const optRe =
    /Title\s*\n(.+?)\s*\nReference code\s*\n(.+?)\s*\nOption ID\s*\n(\d+)\s*\nStatus\s*\n(Active|Deactivated)/g;
  let om;
  while ((om = optRe.exec(bodyText))) {
    options.push({
      title: om[1].trim(),
      reference_code: om[2].trim(),
      option_id: om[3].trim(),
      status: om[4].trim(),
    });
  }

  const pickupMatch = bodyText.match(/Pickup location:\s*\n(.+?)(?:\n|$)/);
  const transportMatch = bodyText.match(/Transportation\s*\n+([\s\S]+?)(?=\n+Refund policy)/);

  let title = "";
  for (const sel of ["h1", "h3"]) {
    for (const el of document.querySelectorAll(sel)) {
      const text = (el.innerText || "").trim();
      if (text && !["Products", "Supply Partner"].includes(text) && text.length > 10) {
        title = text;
        break;
      }
    }
    if (title) break;
  }
  if (!title && refMatch) {
    const tm = bodyText.match(/Product Reference Code:\s*\S+\s*\n(.+?)(?:\n|$)/);
    if (tm) title = tm[1].trim();
  }

  const publicLink = document.querySelector("a[href*='getyourguide.com'][href*='-t']");
  const publicUrl = publicLink ? publicLink.href.split("?")[0] : "";

  return {
    gyg_tour_id: (productIdMatch && productIdMatch[1]) || "",
    reference_code: (refMatch && refMatch[1]) || "",
    product_title: title,
    short_description: shortDesc,
    product_description: fullDesc,
    highlights: pickList("pdp-details-main-information-highlights"),
    inclusions: pickList("pdp-details-main-information-inclusions"),
    exclusions: pickList("pdp-details-main-information-exclusions"),
    pickup_location: pickupMatch ? pickupMatch[1].trim() : "",
    transportation: transportMatch ? transportMatch[1].replace(/\n/g, ", ").trim() : "",
    options,
    public_url: publicUrl,
    details_loaded: Boolean(productIdMatch),
    scraped_at: new Date().toISOString(),
  };
}
return extractGygProductDetails();
