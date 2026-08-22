# Transfera.ae — Design Redesign Handoff
**Prepared for:** Design agent / frontend engineer  
**Date:** June 2026  
**Goal:** Redesign the public-facing site to look human, professional, and modern — removing every generic "AI-generated" pattern — without breaking the admin theming system, i18n/RTL, SEO, or the locked tech stack.

---

## 1. What the product is

**Transfera** is the public booking interface for the **iTour** airport-transfer platform, currently serving Egypt (Hurghada HRG, Cairo CAI, Sharm El Sheikh SSH, Luxor LXR, Aswan ASW, Marsa Alam RMF, Alexandria HBE). It operates as a single brand with:

- A **homepage** with hero + inline booking widget + SEO content sections
- A **booking funnel** (3 steps: vehicle select → flight/extras → passenger details)
- **Destination landing pages** (`/transfers/[slug]`) — one per airport, editorial content + CTA
- A **blog** with travel guides and airport tips
- **Account / booking lookup** pages
- 7 locales: `en`, `ru`, `de`, `pl`, `uk`, `cs`, `ar` — Arabic uses RTL layout

Pricing, brand colours, and font family are **injected by the backend admin** (iTour SiteSettings) at runtime — not hard-coded — so the design system must respect those variables.

---

## 2. Tech stack (locked — do not change)

| Layer | Spec |
|---|---|
| Framework | Next.js 16, App Router, React 19 |
| Language | TypeScript |
| Styling | Tailwind v4 CSS-first (no `tailwind.config.js`) — all tokens in `globals.css` |
| Components | shadcn/ui over Radix UI |
| Variant util | `cva` + `clsx` + `tailwind-merge` |
| Icons | `lucide-react` only |
| Toasts | `sonner` |
| State | `zustand` |
| Maps | Google Maps |
| Deploy | Docker + nginx |
| Fonts | Must be self-hosted or already approved — **adding a Google Fonts CDN call requires a CSP edit** |

---

## 3. Styling system — two layers

### Layer 1: OKLCH design tokens in `globals.css`

The file uses `.website-root { color-scheme: light; }` to force light mode. All colour tokens are defined as OKLCH values. The naming follows shadcn/ui conventions:

```css
/* Key tokens to redefine in the redesign */
--background        /* page bg */
--foreground        /* body text */
--primary           /* CTA buttons, active states */
--primary-foreground
--secondary
--muted             /* subtle bg panels */
--muted-foreground  /* secondary text */
--card              /* card bg */
--border            /* dividers */
--radius            /* global border-radius */
```

### Layer 2: Admin-injected runtime brand variables

These arrive via inline `style` attributes set by iTour SiteSettings and take precedence over the OKLCH tokens for brand-facing elements:

```css
--website-primary        /* main brand colour hex, e.g. #0057FF */
--website-primary-dark   /* darker shade for hover */
--website-secondary      /* accent */
--website-font-family    /* e.g. "Inter, sans-serif" */
--website-radius         /* button / card border radius */
```

Components that show the brand colour (buttons, booking widget, active tabs, CTA strips) **must read `var(--website-primary)`**, not hard-coded values.

### ⚠️ The emerald mismatch — must fix in redesign

Currently, many components hard-code `emerald-*` Tailwind classes (e.g. `bg-emerald-600`, `text-emerald-500`) instead of using `var(--website-primary)`. The token says blue; the admin default is blue/purple; but the UI looks green. **Every instance of hard-coded `emerald-*`, `green-*`, or any colour class on interactive/branded elements must be replaced with the CSS variable equivalents.**

Audit scope — replace these:
- CTA buttons: `bg-emerald-600` → `bg-[var(--website-primary)]`
- Icon accent colours: `text-emerald-500` → `text-[var(--website-primary)]`
- Active tab indicators
- Hover states: `hover:bg-emerald-700` → `hover:bg-[var(--website-primary-dark)]`
- Badge/pill accents
- Feature card icon containers

---

## 4. Current visual audit — what's wrong ("before")

This section documents every pattern that reads as AI-generated or generic. Fix all of them.

### 4.1 Homepage

| Section | Current problem | Human fix |
|---|---|---|
| **Header** | Logo left, nav centre, two duplicate "Book Now" CTAs. Feels like a template clone. | One primary CTA. Add a subtle trust line ("12,000+ transfers booked") near the nav or a thin top bar |
| **Hero** | Full-bleed hero image with white text headline + sub-line. Booking widget is a white card below the headline on the same panel. Reads like a stock landing-page template. | Keep the LCP `<img>` pattern (required). Add a warmer overlay treatment, a badge-style trust mark, and real specificity in copy. Booking widget needs a visual redesign — not just a card, more like a panel with purpose. |
| **"Why Choose Us?" section** | 6 equal-weight cards with identical structure: Lucide icon (emerald) + bold title + 2-sentence description. This is the single most "AI-generated" pattern on the site. Completely generic. | Break the 6-card grid. Use 2–3 hero-value callouts with real weight, then secondary items in a lighter list or timeline. Vary layout — not everything in a grid. Consider one large "anchor" feature (e.g. flight tracking) with a visual and the rest as supporting points. |
| **"How It Works"** | Numbered 1–2–3 with icon + heading + text. Same weight as every other section. | Make the steps feel like a flow — use a horizontal connector or a more editorial layout on desktop. Add micro-copy that sounds human ("Your driver follows your flight — no calls needed"). |
| **"The Difference"** | Bulleted checklist in a coloured strip. Feels like a feature matrix from a SaaS site. | Remove or integrate. If kept, turn it into a statement — e.g. a single strong pull-quote with 3 supporting data points (numbers, not bullets). |
| **Airports section** | Plain `<ul>` list of airport links. | Redesign as a card grid with destination photography, airport code badge, and a "from £X" or "from $X" teaser if available. If no pricing, a hover/active state with a short destination description. |
| **FAQ** | Default accordion. Fine functionally. | Style it with more breathing room, clearer open/close affordance, and section it away from the airports grid visually. |
| **CTA strip** | "Ready to Book Your Transfer?" in an emerald/primary background block with one button. Pure template. | Replace with an editorial moment — a warm full-width section with a real photo inset, a human-sounding headline ("Egypt's airport chaos, solved before you land"), and the CTA. |
| **Footer** | 3 columns, no personality. | Add a tagline, a small trust signal (e.g. star rating aggregate or booking count), keep the 3 columns but give it a darker/warmer background with more visual weight. |

### 4.2 Blog page

Current: wall of text links, no images, no card treatment. All the same date. No visual hierarchy between categories.

Fix: True card grid with:
- Cover image per post (fetch from post data or use placeholder by category)
- Category badge (e.g. "Travel Tips", "Airport Guides", "Egypt Trips")
- Title + 1-sentence excerpt
- Read time estimate
- Hover state with subtle lift

### 4.3 Destination pages (e.g. `/transfers/hurghada`)

Current: breadcrumb label + H1 + body copy + a destinations list + a CTA block. The copy tone on these pages is actually **good** (conversational, specific, not AI-sounding) — preserve it.

Structural problems:
- The hero for destination pages uses the destination image but the layout looks like a blog article rather than a landing page
- The "Popular Routes" section is a plain `<ul>` with no visual weight
- No social proof specific to the destination

Fix:
- Destination hero: large image with a left-aligned text panel (not centred overlay). Badge with airport code + IATA.
- Route cards: replace the list with compact route chips that show origin → destination with an arrow and a "from X" price if available.
- Add a inline booking mini-widget (or a sticky CTA panel on desktop) — these pages are high-intent.
- Trust strip: 3 stats relevant to the destination ("200+ daily pickups in Hurghada", "Avg. 4.9★", "4 vehicle types available")

### 4.4 Booking funnel (`/book`)

Current: 3-step wizard (Vehicle → Flight/Extras → Details). Clean enough but unstyled — feels like a raw form.

The funnel's job is conversion, so:
- Step progress indicator should be visually strong but not distracting
- Vehicle cards need photography (car interior or exterior), capacity icons, luggage icons, price prominently shown
- The "Edit Search" back-link at the top needs to be clearly styled
- Mobile: full-screen step-by-step feels right; desktop: consider a 2-column layout (form left, order summary sticky right)

---

## 5. Design direction — principles

### 5.1 Visual language: "Warm Editorial Travel"

Think: a premium travel brand that actually operates in a hot, sunny, photogenic country.  
Not: a blue SaaS company that happens to offer transfers.

| Attribute | Direction |
|---|---|
| **Colour mood** | Warm sand/stone neutrals as backgrounds, rich brand blue (from `--website-primary`) as accent. Avoid sterile white everywhere. |
| **Photography** | Egypt context — Red Sea blue water, desert light, airport arrivals, vehicles, resort pools. Real moments, not stock-photo composites with fake smiles. |
| **Typography** | Generous leading, clear scale. Headings should feel editorial (slightly larger, looser tracking). Body text comfortable at 16–18px. |
| **Spacing** | Sections need breathing room — 80–120px vertical padding on desktop. Cards need internal padding. |
| **Radius** | Moderate — 8–12px on cards, 6–8px on buttons. Not pill, not sharp. |
| **Shadows** | Soft, warm-tinted (not blue-grey). Cards: `0 2px 16px oklch(0.15 0.02 60 / 0.08)`. |
| **Motion** | Subtle. Cards: `transition: transform 200ms ease, box-shadow 200ms ease` on hover. No parallax, no scroll-triggered animations (CSP risk). |

### 5.2 Trust signals — make them feel earned

The site currently has **zero social proof**. This is a major conversion gap and a key "human" signal.

Add to homepage (pull from real data or use conservative estimates):
- Booking count: "12,000+ transfers completed"
- Review score: "Rated 4.9/5 by travellers" (link to source if available)
- Countries served: "Guests from 40+ countries"
- Years operating: or launch year

Format: 3-stat bar, near the hero CTA or below the booking widget. Horizontal on desktop, stacked on mobile. Use actual numbers — not "thousands" but "12,400+".

### 5.3 Copy tone

The destination page copy is already good — conversational, specific, not AI. Apply that same voice everywhere:
- Avoid: "Our dedicated support team is available around the clock to assist you with any questions or changes to your booking."
- Prefer: "Something change? Call or WhatsApp us any time — we're real people."
- Avoid: "Safe, comfortable, and reliable private transfers across Egypt."
- Prefer: "Your driver's waiting. The price is fixed. Egypt's airport queues are someone else's problem."

---

## 6. Design tokens — redesign values

These go in `globals.css` under `.website-root`. Keep all existing token names — only update values.

```css
.website-root {
  /* Backgrounds — warm off-white, not pure white */
  --background: oklch(0.985 0.003 75);        /* warm white */
  --card: oklch(1 0 0);                        /* pure white for cards */
  --muted: oklch(0.965 0.006 75);              /* warm light grey panels */
  --muted-foreground: oklch(0.52 0.025 250);  

  /* Foreground — slightly warm dark, not pure black */
  --foreground: oklch(0.18 0.015 250);
  --card-foreground: oklch(0.18 0.015 250);

  /* Border — very subtle */
  --border: oklch(0.9 0.005 75);
  --input: oklch(0.9 0.005 75);

  /* Primary — reads from admin var; fallback to a confident blue */
  /* NOTE: do not change --primary directly in most components.      */
  /* Use var(--website-primary) for branded buttons/accents.         */
  --primary: oklch(0.48 0.22 260);            /* fallback if admin not set */
  --primary-foreground: oklch(1 0 0);

  /* Secondary / accent */
  --secondary: oklch(0.965 0.006 75);
  --secondary-foreground: oklch(0.18 0.015 250);

  /* Radius */
  --radius: 0.625rem;                         /* 10px base */

  /* Shadow warmth — used in component CSS */
  --shadow-card: 0 2px 16px oklch(0.15 0.02 60 / 0.07);
  --shadow-card-hover: 0 8px 32px oklch(0.15 0.02 60 / 0.13);
}
```

### Elevation scale (add to globals.css)

```css
:root {
  --elevation-1: 0 1px 3px oklch(0.15 0.02 60 / 0.06);
  --elevation-2: 0 2px 8px oklch(0.15 0.02 60 / 0.08);
  --elevation-3: 0 4px 20px oklch(0.15 0.02 60 / 0.10);
  --elevation-4: 0 8px 40px oklch(0.15 0.02 60 / 0.14);
}
```

---

## 7. Typography

**Font stack decision:** The admin injects `--website-font-family`. The redesign should default to a humanist sans-serif that reads warmly.

Recommended self-hosted option: **Inter** (already common in Next.js projects via `next/font/google` with `display: swap` — this works **without a CSP change** because `next/font` downloads at build time, not runtime).

```tsx
// app/layout.tsx
import { Inter } from 'next/font/google'
const inter = Inter({ subsets: ['latin', 'latin-ext'], display: 'swap' })
```

If `--website-font-family` is set by admin, it overrides. If not set, Inter is the fallback.

### Type scale

| Role | Size | Weight | Line-height | Tracking |
|---|---|---|---|---|
| `h1` (hero) | `clamp(2.25rem, 4vw, 3.5rem)` | 700 | 1.15 | -0.02em |
| `h2` (section heading) | `clamp(1.75rem, 3vw, 2.5rem)` | 700 | 1.2 | -0.015em |
| `h3` (card heading) | `1.25rem` | 600 | 1.3 | -0.01em |
| Body | `1rem` / `1.0625rem` | 400 | 1.65 | 0 |
| Small / caption | `0.875rem` | 400 | 1.5 | 0.01em |
| Label / badge | `0.75rem` | 600 | 1.2 | 0.04em uppercase |

---

## 8. Component-by-component redesign specs

### 8.1 Header / Navigation

**Current:** Logo left | Nav links centre | Language picker | `My Account` + `Book Now` button right.  
Two "Book Now" buttons visible simultaneously (one in nav, one as primary CTA).

**Redesign:**

```
[Logo]                    [Home] [Routes ▾] [Blog]     [EN ▾]  [Book Now →]
```

- Logo: SVG, left-aligned. Max height 32px. Link to `/{locale}`.
- Nav links: regular weight, `--foreground` colour. Hover: `--website-primary`.
- "Routes" becomes a dropdown (already exists) — style with a clean popover, destination cards with flag/icon.
- Language picker: text + globe icon, clean dropdown.
- **Single** CTA button, right-aligned: solid `--website-primary` fill, white text, `--radius` rounded, 40px height.
- Remove the second "Book Now" from nav. The hero widget serves that purpose.
- On scroll > 60px: header gets `backdrop-blur-md bg-white/90 border-b border-[--border]` — a frosted glass effect.
- Mobile: hamburger → full-screen slide-in drawer. Language + Book Now inside drawer.
- RTL (`dir="rtl"`): logo moves right, nav left, CTA left — Tailwind's `rtl:` variants handle this automatically.

### 8.2 Hero section

**Current:** Full-bleed image, white headline + subline centred, booking widget card below.

**Redesign (preserve the `<img>` LCP pattern — do not convert to CSS background):**

```
┌─────────────────────────────────────────────────────┐
│  [Hero Image — full bleed, 70vh min desktop]        │
│  Overlay: linear-gradient(to right,                 │
│    oklch(0.1 0.02 250 / 0.75) 0%,                   │
│    oklch(0.1 0.02 250 / 0.2) 60%,                   │
│    transparent 100%)                                 │
│                                                      │
│  ┌──────────────────────────────┐                   │
│  │ [badge] Private Transfers    │                   │
│  │                              │                   │
│  │ H1: Egypt's airports,        │                   │
│  │     handled.                 │                   │
│  │                              │                   │
│  │ Sub: Fixed prices. Your      │                   │
│  │ driver waiting. No queues.   │                   │
│  │                              │                   │
│  │ ★★★★★ 4.9 · 12,400 transfers │                   │
│  └──────────────────────────────┘                   │
│                                                      │
│  ┌── Booking Widget ─────────────────────────────┐  │
│  │ [Airport Transfer] [City to City]              │  │
│  │ [One Way] [Return]                             │  │
│  │ [From ▾] [To ▾] [Date] [Time] [Pax] [Search→] │  │
│  └────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

Key details:
- The `<img>` tag stays as the LCP element — wrap it with `position: absolute inset-0 w-full h-full object-cover`
- The gradient overlay goes on a sibling `<div>` with `absolute inset-0` (no content in the img itself)
- Headline is left-aligned on desktop (not centred). Content area is max-w-2xl.
- The trust badge below the headline: `★★★★★ 4.9 — 12,400+ transfers` — white text, 14px
- The booking widget floats at the bottom of the hero, slightly overlapping the next section (negative bottom margin) — gives depth
- On mobile: headline centred, widget becomes full-width below hero, no overlap

**Booking widget redesign:**
- White background, `--elevation-3` shadow, `--radius` rounding
- Tabs (`Airport Transfer` / `City to City`) use `--website-primary` for active underline
- Direction chips (`One Way` / `Return`) styled as pill-toggles, not plain tabs
- Form fields: clean with floating labels or clear placeholder text, 44px height minimum
- Search button: full `--website-primary` background, same height as fields, text "Search transfers →"
- On mobile: fields stack vertically, button full-width

### 8.3 Trust stats bar

**New section — insert between hero and "Why Choose Us":**

```
┌──────────────────────────────────────────────────────────┐
│   12,400+          4.9 / 5          40+           24/7   │
│   Transfers     Avg. rating      Countries      Support  │
└──────────────────────────────────────────────────────────┘
```

- Background: `--muted` (warm off-white) or a very light `--website-primary` tint at 5% opacity
- 4 columns, centred, generous padding (py-10)
- Number: 2.5rem, 700 weight, `--website-primary` colour
- Label: 0.875rem, muted foreground
- Dividers between columns on desktop (subtle `--border`)
- Mobile: 2×2 grid

### 8.4 "Why Choose Us?" — Features section

**Redesign completely.** Replace the 6-card grid with an **anchor + support** layout.

Desktop layout:

```
[Section label: "Why Transfera"]
[H2: "Less airport stress. More holiday."]

┌──────────────────────────────────┬────────────────────┐
│                                  │  Flight Tracking    │
│  [Large: Flight tracking visual  │  Sub-point text     │
│   or illustration — a phone      ├────────────────────┤
│   showing a flight tracked]      │  Meet & Greet       │
│                                  │  Sub-point text     │
│  "We watch your flight so you    ├────────────────────┤
│   don't have to."                │  Fixed Price        │
│                                  │  Sub-point text     │
│  Sub: Delays, early arrivals,    ├────────────────────┤
│  gate changes — your driver      │  Free Cancellation  │
│  always knows.                   │  Sub-point text     │
└──────────────────────────────────┴────────────────────┘
```

- Left panel: one anchor feature with larger icon/visual, larger headline, 2-sentence human description
- Right panel: 4 compact feature rows, each with small icon, bold 1-line heading, 1-line description
- Anchor feature cycles or is fixed to Flight Tracking (most differentiating)
- Background: white card on `--muted` section background

Mobile: anchor first, features below as a 2-column grid.

### 8.5 "How It Works" — Steps section

**Redesign with a flow feel:**

```
[H2: "Book in under 2 minutes"]

  [1]──────────────────[2]──────────────────[3]
  Search               Book & Pay            Travel
  
  Enter pickup,        Details and           Driver's
  drop-off, date       payment — online      waiting with
  and passengers.      or on arrival.        your name.
```

- Horizontal on desktop with a connecting line between steps (CSS border, `--border` colour)
- Step number: circular badge, `--website-primary` background, white number
- Connector line is `--border` colour, 1px
- Each step: icon above number on mobile, or step number + icon side by side
- Tone of copy: keep it short and human (see examples above)

### 8.6 Airports / Destinations section

**Replace plain `<ul>` with a destination card grid:**

```
[H2: "Every major Egyptian airport"]

┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ [photo]  │ │ [photo]  │ │ [photo]  │ │ [photo]  │
│ HRG      │ │ CAI      │ │ SSH      │ │ LXR      │
│ Hurghada │ │  Cairo   │ │  Sharm   │ │  Luxor   │
│ →        │ │ →        │ │ →        │ │ →        │
└──────────┘ └──────────┘ └──────────┘ └──────────┘
```

- 4-column grid desktop, 2-column tablet, 1-column mobile
- Card: 200px height min, destination photo as background, dark gradient overlay from bottom
- IATA code badge top-left: white text on semi-transparent dark pill
- City name bottom-left: white, 1.125rem, 600 weight
- Hover: slight scale (1.02) + brighter overlay
- Links to `/transfers/[slug]`
- Destinations without a photo: use a solid warm-tinted placeholder

### 8.7 CTA strip ("Ready to Book?")

**Replace with editorial section:**

```
┌─────────────────────────────────────────────────────────┐
│  [Full-width, warm background — deep blue or warm dark] │
│                                                          │
│  [Left: editorial text]    [Right: subtle img inset]    │
│                                                          │
│  Egypt's airport queues,                                │
│  solved before you land.                                │
│                                                          │
│  Get an instant quote —                                 │
│  takes less than 90 seconds.                            │
│                                                          │
│  [Book My Transfer →]                                   │
└─────────────────────────────────────────────────────────┘
```

- Background: `--website-primary` or a deep warm dark (oklch 0.18 0.08 250)
- Text: white
- Button: white background, `--website-primary` text — inverted
- Right side on desktop: a rotated/offset card showing a mock booking confirmation, or a small destination photo with white card border
- Mobile: stacked, image hidden or shown above text

### 8.8 FAQ section

Minimal changes needed — accordion is functionally fine. Style improvements:

- Increase padding (py-5 px-0 per item)
- Question: 1rem, 600 weight, `--foreground`
- Open indicator: `+` / `−` or chevron in `--website-primary`
- Answer: `--muted-foreground`, 1.65 line-height, slight top padding
- Container: max-w-3xl centred — FAQs should feel focused, not full-width

### 8.9 Blog page

**Full redesign of the listing page:**

- Remove the current text-only link list
- Implement a proper card grid: 3-column desktop, 2-column tablet, 1-column mobile
- Card structure:
  ```
  ┌─────────────────────┐
  │  [Cover image 16:9] │
  │  [Category badge]   │
  ├─────────────────────┤
  │  Title              │
  │  Excerpt (2 lines)  │
  │  Date · Read time   │
  └─────────────────────┘
  ```
- Category badge: pill, category-specific colour (e.g. "Travel Tips" = warm amber tint, "Airport Guides" = blue tint)
- Card hover: title colour shifts to `--website-primary`, subtle shadow lift
- If no cover image available from CMS: generate a gradient placeholder using the category colour

### 8.10 Destination pages (`/transfers/[slug]`)

**Hero:**
- Two-column layout on desktop: text left (H1, sub, trust stats, CTA), image right
- Image: destination photo, rounded-xl, slight shadow — NOT a full-bleed overlay
- Mobile: image above, text below
- H1 should be the airport name, not a generic phrase
- IATA code badge near the H1 (e.g. `HRG` in a muted pill)

**Inline booking mini-widget:**  
Add a compact version of the booking widget immediately below the hero (destination pre-filled). High-intent visitors land here; give them a way to book without scrolling back to the homepage.

**Route chips:**
Replace the current `<ul>` list:
```
[→ El Gouna] [→ Makadi Bay] [→ Soma Bay] [→ Sahl Hasheesh] [→ Hurghada City]
```
Styled as interactive chips — border, hover fill, arrow icon. On click: scroll to booking widget with destination pre-filled.

**Trust strip (destination-specific):**
```
✓ Fixed price · No hidden fees    ✓ Free cancellation 24h    ✓ Flight tracking
```
Horizontal on desktop, 3 ticks in a strip. Simple but visible.

### 8.11 Footer

**Redesign with more warmth and brand presence:**

```
┌──────────────────────────────────────────────────────────┐
│  [Dark background — oklch 0.15 0.02 250 or similar]      │
│                                                          │
│  Transfera                  Quick Links   Contact        │
│  [logo white version]       Home          support@...    │
│  [tagline]                  Book Now      +20 100...     │
│  Egypt's airport transfer   Destinations  WhatsApp       │
│  specialists.               Blog                        │
│                             Track Booking               │
│                                                          │
│  ★★★★★ 4.9 — 12,400+ transfers completed               │
│  ──────────────────────────────────────────────────────  │
│  © 2026 Transfera. All rights reserved.  [Privacy] [T&C] │
└──────────────────────────────────────────────────────────┘
```

- Background: dark (not black — warm dark oklch)
- Text: white / white/70 for secondary
- Logo: white version of the SVG
- Tagline under logo: "Egypt's airport transfer specialists." or similar, `--muted-foreground` equivalent for dark bg
- Bottom bar: copyright left, legal links right, a single thin divider
- Add the trust stat line above the bottom bar for a final conversion nudge
- Mobile: single column, logo top, then links, then contact, then copyright

---

## 9. Booking funnel (`/book`) — enhancement notes

The funnel is conversion-critical. Keep the 3-step structure but improve visual quality:

**Step progress bar:**
```
[●]─────────────[○]─────────────[○]
 1 Vehicle       2 Flight         3 Details
```
- Completed steps: `--website-primary` filled circle
- Active step: `--website-primary` circle + `--website-primary` label
- Future step: grey circle + muted label
- Connector line: `--border`, 1px

**Vehicle cards (Step 1):**
- Large cards (not a table)
- Vehicle image: car photo, not icon — 200px wide on desktop
- Capacity + luggage in icon-rows (person icon × N, bag icon × N)
- Price: large, right-aligned, `--website-primary` colour
- "Select" button: full-width at card bottom
- Selected state: card gets `ring-2 ring-[--website-primary]` + a subtle primary bg tint

**Desktop layout:**
- Consider a sticky right panel (order summary / your trip details) while the form is on the left
- This is a standard ecommerce pattern that significantly reduces drop-off

---

## 10. RTL / Arabic notes

Tailwind v4 supports `rtl:` variants natively. Key rules:

- Never use `ml-*` / `mr-*` directly on layout elements — use `ms-*` / `me-*` (margin-start / margin-end) which flip for RTL
- Flexbox `flex-row` reverses correctly if you use `dir="rtl"` on the HTML element
- Text alignment: use `text-start` / `text-end` not `text-left` / `text-right`
- Icons that imply direction (arrows, chevrons): wrap in `rtl:scale-x-[-1]` to flip
- The booking widget has a `dir` prop driven by the locale — ensure all new sections inherit it from the page root

Arabic font note: if `--website-font-family` is set to an Arabic font by the admin, it covers the Arabic locale. For the redesign, ensure the latin font fallback chain ends in `system-ui` so Arabic characters always have a reasonable fallback.

---

## 11. Imagery strategy

All images must be served from **approved domains** (CSP rule). The site currently uses:
- `transfera.ae` (self-hosted uploads)
- `fulvago.itourtt.cloud` (admin-uploaded destination images — seen in OG images)

**Do not add new image CDN domains without a CSP edit.**

For the redesign:
- Destination card photos: already uploaded to `fulvago.itourtt.cloud` per the OG image URLs — reuse these
- Hero image: already at `transfera.ae/uploads/...` — keep
- Blog cover images: must come from the CMS (self-hosted) — design the card to gracefully handle missing images with a gradient placeholder
- No Unsplash/Pexels CDN URLs unless those domains are added to the CSP

**Placeholder gradient for missing images:**
```css
background: linear-gradient(135deg, 
  oklch(0.6 0.12 250) 0%, 
  oklch(0.45 0.18 280) 100%);
```

---

## 12. Constraints — do not break

| Constraint | Detail |
|---|---|
| LCP `<img>` pattern | The hero image must remain an `<img>` tag with `priority` prop (Next.js Image) or `fetchpriority="high"`. Do not convert to CSS background. |
| Admin theming variables | All branded colours on interactive elements must use `var(--website-primary)` / `var(--website-primary-dark)`. Never replace with hard-coded Tailwind colour classes. |
| SEO / JSON-LD / metadata | Do not remove or reorder the `<head>` metadata blocks. The `canonical`, OG tags, and JSON-LD structured data must remain intact. |
| i18n `[locale]` routing | All routes are prefixed `/[locale]/...`. All internal links must use the current locale prefix. |
| Arabic RTL | Use `ms-*`/`me-*` margin/padding utilities and `text-start`/`text-end` on all new components. |
| shadcn/ui Radix | Use shadcn components for all interactive primitives (dialogs, dropdowns, accordions, tabs). Don't replace with custom implementations. |
| CSP | No new external script, font, or image domains without editing the nginx CSP header config. |
| Sonner toasts | Keep — don't replace the toast system. |
| Zustand store | Don't touch booking state management. |

---

## 13. Files to change

```
app/
  globals.css                  ← Token updates (Section 6)
  [locale]/
    page.tsx                   ← Homepage section redesign
    layout.tsx                 ← Header + font import
    book/
      page.tsx                 ← Funnel step layout
    transfers/[slug]/
      page.tsx                 ← Destination page layout
    blog/
      page.tsx                 ← Blog card grid

components/
  layout/
    Header.tsx                 ← Nav redesign
    Footer.tsx                 ← Footer redesign
  home/
    HeroSection.tsx            ← Hero + overlay redesign
    BookingWidget.tsx          ← Widget visual redesign
    TrustBar.tsx               ← NEW — trust stats bar
    FeaturesSection.tsx        ← Anchor + support layout
    HowItWorks.tsx             ← Steps flow redesign
    DestinationsGrid.tsx       ← Card grid (replace list)
    CtaSection.tsx             ← Editorial CTA redesign
  blog/
    PostCard.tsx               ← NEW card component
  destination/
    DestinationHero.tsx        ← Two-column hero
    RouteChips.tsx             ← NEW route chip component
  booking/
    VehicleCard.tsx            ← Photography + pricing redesign
    StepProgress.tsx           ← Progress bar redesign
```

---

## 14. Do / Don't summary

| ✅ DO | ❌ DON'T |
|---|---|
| Use `var(--website-primary)` for all branded colours | Hard-code `emerald-*`, `green-*`, or any specific Tailwind colour on interactive elements |
| Use `ms-*`/`me-*` for directional spacing | Use `ml-*`/`mr-*` on layout-sensitive elements |
| Use `next/font` for font loading | Add a `<link>` to Google Fonts CDN (CSP blocks it) |
| Keep the `<img>` LCP pattern in the hero | Convert the hero image to a CSS `background-image` |
| Use shadcn/ui primitives for interactive components | Roll custom dialog/dropdown/accordion implementations |
| Serve images from `transfera.ae` or `fulvago.itourtt.cloud` | Use Unsplash/Pexels/other CDN image URLs |
| Read admin brand variables (`--website-primary`, `--website-font-family`) | Ignore the admin variables and hard-code brand values |
| Use `text-start`/`text-end` for text alignment | Use `text-left`/`text-right` on localised text |
| Keep JSON-LD and metadata blocks intact in page files | Reorganise or remove structured data |
| Test every new section in Arabic RTL | Only test in English |

---

## 15. Quick-start commands

```bash
# Install / dev
npm install
npm run dev        # localhost:3000

# Build check (catches type errors)
npm run build

# Lint
npm run lint

# Docker build (mirrors production)
docker build -t transfera-web .
docker run -p 3000:3000 transfera-web
```

To test RTL: navigate to `/ar` on the dev server.  
To test admin theming without the backend: temporarily add to `globals.css`:
```css
:root {
  --website-primary: #0057FF;
  --website-primary-dark: #003FCC;
  --website-font-family: "Inter", sans-serif;
}
```
Remove before deploying.

---

## 16. Visual QA checklist (before handing back)

- [ ] No `emerald-*` or `green-*` classes remain on interactive/branded elements
- [ ] Hero `<img>` has `fetchpriority="high"` or Next.js `priority` prop
- [ ] All internal links include the `[locale]` prefix
- [ ] Arabic (`/ar`) layout is RTL — no overlapping or reversed elements
- [ ] Admin theme variables (`--website-primary` etc.) correctly override brand colours
- [ ] All new image URLs are from `transfera.ae` or `fulvago.itourtt.cloud`
- [ ] Booking widget tabs work (Airport Transfer / City to City, One Way / Return)
- [ ] Mobile booking widget: all fields accessible and tappable (min 44px touch target)
- [ ] Footer copyright year is dynamic (`new Date().getFullYear()`)
- [ ] JSON-LD structured data blocks are present on homepage and destination pages
- [ ] No new `<link rel="stylesheet" href="...">` or `<script src="...">` pointing to unapproved external domains
- [ ] Sonner toast notifications still work on booking confirmation steps
- [ ] shadcn/ui Radix dropdowns in nav (Routes) and booking widget (airport select) still function
