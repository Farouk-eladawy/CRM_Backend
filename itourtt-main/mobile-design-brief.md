# Transfera Mobile App — UI/UX Design Brief

**Product:** Transfera (the consumer brand of the iTour Transport & Traffic platform)
**App:** iTour Booking — the B2C guest transfer app (React Native, iOS + Android)
**Prepared for:** Graphic / product designer creating the mobile UI/UX
**Date:** June 2026
**Status of build:** A React Native monorepo and the guest app skeleton already exist (screens, navigation, booking store, shared theme). This brief asks the designer to deliver a polished, branded visual system + screen designs that the existing engineering scaffold can be re-skinned to match.

> The desktop/web redesign direction lives in `transfera-design-handoff.md` (same repo root). This mobile brief is its companion — same brand, adapted to native mobile patterns. Where the two could diverge, **the web handoff is the source of truth for brand language**; this doc is the source of truth for **mobile screens, flows, and native behavior**.

---

## 0. Repositories & Resources (everything needed to finish the job)

All work happens against the iTour codebase. The designer/engineer needs access to these:

| Resource | URL / Location | What it is | Why you need it |
|---|---|---|---|
| **Main monorepo** | `https://github.com/mg-gouda/itourtt` (SSH: `git@github.com:mg-gouda/itourtt.git`) | Dashboard frontend, NestJS backend, **and the React Native mobile apps** | The mobile app you are designing for lives here under `/mobile`. This is where design tokens, screens, and components are implemented. |
| → Mobile RN monorepo | `/mobile` inside the main repo | Yarn workspaces: `apps/guest` (this app), `apps/driver`, `apps/rep`, `apps/supplier`, `packages/ui`, `packages/shared` | The guest app skeleton + shared theme/UI library to re-skin. See `mobile/SETUP.md`. |
| → Backend API | `/backend` inside the main repo | NestJS REST API; serves all `/api/public/*` endpoints the guest app calls | Defines the real data shapes every screen renders. |
| → Admin frontend | `/frontend` inside the main repo | Next.js admin dashboard + parked `app/(public)` booking funnel + `components/website/*` | Reference implementation of the booking widget/funnel that mobile mirrors. |
| **B2C public website (live design reference)** | `https://github.com/mg-gouda/iTourTT-B2CSite` (SSH: `git@github.com:mg-gouda/iTourTT-B2CSite.git`) | Standalone Next.js 16 / React 19 / Tailwind v4 public site (the "Transfera" website) | **The primary visual reference.** The mobile app must feel like the same brand. This is the codebase the web design handoff targets. |
| **Live website** | `https://transfera.ae` | Production B2C site | See the brand in the wild — colors, copy tone, booking widget, destination pages, blog. |
| **Live backend API** | `https://fulvago.itourtt.cloud/api` | Production API base the apps consume | Hit `/public/locations`, `/public/vehicle-types`, `/public/quote` to see real data the app displays. |
| **Web→mobile design handoff** | `transfera-design-handoff.md` (main repo root) | The web redesign brief ("Warm Editorial Travel") | Brand language, color/type system, tone, component specs. Mobile inherits all of it. |
| **Mobile setup guide** | `mobile/SETUP.md` (main repo) | Local dev, Firebase, Stripe, CI/CD, build & release | How to run the guest app on a simulator to see designs live. |
| **Separation plan** | `B2C-WEBSITE-SEPARATION-PLAN.md` (main repo root) | History/architecture of the B2C site split | Context on how web + backend + mobile relate. |

**Key files inside the mobile guest app (where designs get applied):**
- `mobile/packages/shared/src/theme/` — `colors.ts`, `typography.ts`, `spacing.ts` (design tokens)
- `mobile/packages/ui/src/` — shared component library (`Button`, `Card`, `Badge`, `Input`, `EmptyState`, `Skeleton*`, `Dialog`, etc.)
- `mobile/apps/guest/src/screens/` — the 8 guest screens
- `mobile/apps/guest/src/components/` — `VehicleTypeCard`, `PriceSummary`, `StepIndicator`, `ExtrasSelector`, `LocationPicker`
- `mobile/apps/guest/src/navigation/RootNavigator.tsx` — stack navigation
- `mobile/apps/guest/src/stores/booking-store.ts` — the booking funnel state (defines every field a screen collects)

> Note on auth model: the public booking flow is **guest-first** — no account is required to book. There is also a customer login on the web (role `B2C_CLIENT`, password = booking phone number) used to view bookings. For mobile v1, "account" = **booking lookup by reference + email**, not a full login (see §10 Out of Scope).

---

## 1. Project Overview

**What it does.** Transfera is a private airport-transfer booking service operating across Egypt's major airports — Hurghada (HRG), Cairo (CAI), Sharm El Sheikh (SSH), Luxor (LXR), Aswan (ASW), Marsa Alam (RMF), Alexandria (HBE). A traveller books a fixed-price private car between an airport and their hotel/zone (or city-to-city); a driver tracks their flight and meets them on arrival. Behind the scenes it's powered by the iTour dispatch/traffic platform, but the consumer never sees that complexity.

**The mobile app** is the guest booking app: search a transfer → pick a vehicle → enter details → pay (or pay on arrival) → get a confirmation → track/look up the booking later.

**Target audience (B2C).**
- International leisure travellers flying into Egyptian resort destinations (primarily Red Sea: Hurghada, Sharm, Marsa Alam) — UK, Germany, Russia, Poland, Ukraine, Czech, plus Arabic-speaking regional travellers.
- Booking on mobile, often **before or during travel** (at home pre-trip, or just-landed on airport Wi-Fi/roaming).
- Not power users. Many are anxious first-time visitors who worry about airport taxis, scams, and language barriers.

**Core value proposition.** *"Your driver's waiting. The price is fixed. Egypt's airport queues are someone else's problem."*
- **Fixed, upfront price** — no haggling, no meter.
- **Flight tracking** — the driver knows if you're early or delayed.
- **Meet & greet** — a named pickup, no hunting for a taxi.
- **Pay online or on arrival** — flexible.
- **Free cancellation** within the allowed window.

**Personality.** Warm, human, reassuring, specific. A premium travel brand that *actually operates in a hot, sunny, photogenic country* — **not** a sterile blue SaaS app. Avoid generic "AI-generated" patterns (equal-weight icon-card grids, vague reassurance copy).

---

## 2. Brand Identity

> All values below are extracted from the codebase (`mobile/packages/shared/src/theme/*`, `frontend/src/components/website/*`) and the web handoff. The web layer themes brand color/font **at runtime** from admin settings (`--website-primary`, `--website-font-family`); the mobile app currently bakes the same blue. Designs should treat the blue as the brand default but keep brand color as a **single source token** so it can be re-pointed.

### 2.1 Color palette

**Brand / primary (currently hard-coded in the guest app — `HomeScreen`, `SearchScreen`, `RootNavigator`):**

| Token | Hex | Use |
|---|---|---|
| Primary blue | `#1D4ED8` | CTAs, active states, header tint, price emphasis, selected vehicle ring |
| Primary dark | `#1E3A5F` | Hover/pressed, deep accents |
| Primary light | `#DBEAFE` / `#EFF6FF` | Tints, selected backgrounds, subtle fills |
| Success green | `#16A34A` | Confirmation screen, success states |

**Neutrals — light mode (`lightColors`):**

| Token | Hex |
|---|---|
| background | `#FFFFFF` |
| foreground (text) | `#09090B` |
| card | `#FFFFFF` |
| muted (panels) | `#F4F4F5` |
| muted-foreground (secondary text) | `#71717A` |
| border / input | `#E4E4E7` |
| ring | `#A1A1AA` |
| destructive | `#EF4444` |

**Neutrals — dark mode (`darkColors`) — the app already ships light/dark/system:**

| Token | Hex |
|---|---|
| background | `#09090B` |
| foreground | `#FAFAFA` |
| card | `#18181B` |
| muted | `#27272A` |
| muted-foreground | `#A1A1AA` |
| border | `rgba(255,255,255,0.1)` |
| destructive | `#DC2626` |

**Status colors (job/booking badges — light):** PENDING `#DC2626` on `#FEF2F2`; ASSIGNED `#059669` on `#ECFDF5`; IN_PROGRESS `#2563EB` on `#EFF6FF`; COMPLETED `#16A34A` on `#F0FDF4`; CANCELLED `#71717A` on `#F4F4F5`; NO_SHOW `#EA580C` on `#FFF7ED`. (Dark-mode variants exist in `statusColorsDark`.)

**Service-type colors:** ARR `#1D4ED8`/`#DBEAFE`; DEP `#DC2626`/`#FEE2E2`; DAY_TOUR `#059669`/`#D1FAE5`; ONE_WAY_TRANSFER `#4338CA`/`#E0E7FF`; TWO_WAY_TRANSFER `#7C3AED`/`#EDE9FE`.

> **⚠️ Brand-warmth gap to close (carried from web handoff).** The current neutrals are pure cool grey/white (shadcn defaults). The web redesign moves to **warm off-white** backgrounds and **warm-tinted shadows** for an "editorial travel" feel. The designer should propose a warm neutral ramp for mobile too (e.g. backgrounds nudged toward warm `#FBFAF8`-ish, soft warm shadows) rather than clinical white — while keeping the blue as the brand accent. Don't ship sterile white everywhere.

### 2.2 Typography

System fonts are used today (`Platform.select`: iOS `System` / Android `Roboto`). The web brand defaults to **Inter**. Recommendation: ship Inter (or the admin-set brand font) bundled in the app for cross-platform brand consistency; fall back to system. Confirm with stakeholders before bundling a custom font.

**Type scale (from `typography.ts` — px / weight / line-height):**

| Role | Size | Weight | Line-height | Tracking |
|---|---|---|---|---|
| h1 | 32 | 700 | 40 | -0.5 |
| h2 | 24 | 700 | 32 | -0.3 |
| h3 | 20 | 600 | 28 | — |
| h4 | 18 | 600 | 26 | — |
| body | 16 | 400 | 24 | — |
| bodyMedium | 16 | 500 | 24 | — |
| bodySm | 14 | 400 | 20 | — |
| label | 14 | 600 | 20 | — |
| button | 16 | 600 | 24 | — |
| buttonSm | 14 | 600 | 20 | — |
| caption | 12 | 400 | 16 | — |
| tabLabel | 11 | 500 | 14 | — |

Designs may extend this (e.g. a larger hero display style), but keep names stable so engineering can map 1:1.

### 2.3 Spacing & radius (from `spacing.ts`)

- **Spacing scale (px):** 0, 2, 4, 6, 8, 10, 12, 16, 20, 24, 28, 32, 36, 40, 48, 56, 64, 80.
- **Radius (px):** sm 4, md 6, lg 8, xl 12, 2xl 16, 3xl 20, full 9999. Web handoff direction: moderate radius — **8–12px on cards, 6–8px on buttons** (not pill, not sharp).
- **Touch targets:** minimum 44×44px (already a web QA requirement; mandatory on mobile).

### 2.4 Logo usage

- App brand mark: `iTour` wordmark today (`HomeScreen` shows "iTour"). The consumer brand is **Transfera** — **clarify with stakeholders which mark the app uses** (likely Transfera for B2C). Logo asset lives at `mobile/preview/public/itourtt-logo.svg`; web uses an SVG logo.
- Keep the logo as SVG/vector. Provide light and **white/dark-mode** variants.
- Clear space: minimum 1× the logo's cap-height on all sides. Don't place on busy photo areas without a scrim.
- App icon: assets under `mobile/apps/guest/ios/.../Images.xcassets/AppIcon.appiconset` and `mobile/assets/icons/` — the designer should deliver a full icon set + splash (BootSplashLogo imageset exists).

### 2.5 Tone & personality (from real copy)

- **Do:** specific, human, reassuring. *"Airport transfers made simple." / "Your driver follows your flight — no calls needed." / "Something change? Call or WhatsApp us any time — we're real people."*
- **Don't:** generic SaaS reassurance. Avoid *"Our dedicated support team is available around the clock to assist you with any questions."*
- Service-type framing for guests: **Arrival = "Airport to hotel"**, **Departure = "Hotel to airport"** (already in `SearchScreen`).

---

## 3. Core User Flows

1. **Book a transfer (primary funnel)** — Home → Search (service type, route, date, time, pax) → Choose vehicle (live quotes + extras) → Your details (guest + flight info) → Payment (online or pay-on-arrival) → Confirmation (booking ref). State is held in `booking-store.ts`.
2. **Track / look up a booking** — Home → Track Booking → enter booking reference + email → Booking detail (status, route, driver/vehicle when assigned, evidence photos on completed jobs) → optional cancel.
3. **Browse destinations** *(parity with web; see scope)* — explore airport/destination landing content → start a pre-filled booking.
4. **Read travel guides / blog** *(parity with web; scope-dependent)* — browse posts → read article.
5. **App settings** — light/dark/system theme (already present), language, contact/support (WhatsApp/call).
6. **Onboarding (new for mobile)** — first-launch intro: what Transfera is + value props + notification/location permission priming.

---

## 4. Screen Inventory

Group A screens already exist in code and need a visual redesign. Groups B–D are new-for-mobile or parity-with-web; mark each in design as **v1** or **later**.

### A. Booking funnel & lookup (exist today — redesign these)
1. **Home** (`HomeScreen`) — brand header, primary "Book a transfer" CTA, "Track booking" secondary, theme picker. *Redesign into a warm hero with value props + trust signals.*
2. **Search / Transfer Details** (`SearchScreen`) — service type (Arrival/Departure) toggle, location pickers (from/to via `LocationPicker`), date picker, time picker, pax stepper, Step indicator.
3. **Choose Vehicle** (`VehicleSelectScreen`) — list of vehicle types with **live price quotes** (`VehicleTypeCard`), extras selector (booster seat, baby seat, wheelchair via `ExtrasSelector`), price summary.
4. **Your Details** (`GuestDetailsScreen`) — name, email, phone, country, flight no., carrier, terminal, notes.
5. **Payment** (`PaymentScreen`) — method (Online / Pay on arrival), gateway (Stripe / Egypt bank / Dubai bank) where online.
6. **Confirmation** (`ConfirmationScreen`) — submits booking, shows booking reference + success, next actions.
7. **Track Booking / Lookup** (`BookingLookupScreen`) — booking ref + email form.
8. **Booking Detail** (`BookingDetailScreen`) — full booking status, route, assignment (vehicle/driver), evidence photos, cancel.

### B. New for mobile (v1)
9. **Onboarding / first-run** — 2–3 intro slides + permission priming (notifications, location).
10. **Settings** — theme (exists inline today; give it a home), language picker, support links, legal.
11. **Empty / error / offline states** — designed variants for every list/detail (components exist: `EmptyState`, `ErrorBanner`, `OfflineBar`).
12. **Loading skeletons** — funnel + detail (`Skeleton`, `SkeletonList`, `SkeletonProfile`, `SkeletonJobCard` exist).

### C. Parity with web (scope-dependent — recommend later)
13. **Destinations index + destination detail** (`/transfers/[slug]` on web) — editorial airport landing pages.
14. **Blog index + article** — travel guides / airport tips.
15. **FAQ** — accordion.

### D. Mobile-native chrome
16. **Tab bar / navigation shell** — decide bottom-tab vs stack-only (see §9).
17. **Push notification templates** — booking confirmed, driver assigned, pickup reminder, status changes.

---

## 5. Key UI Components

Reusable components already in the shared library (`packages/ui`) + guest app — each needs a mobile-native visual treatment:

**Shared library (`@itour/ui`):** `Button`, `Card`, `Badge`, `Input`, `LoadingSpinner`, `EmptyState`, `ErrorBanner`, `OfflineBar`, `StatusBadge`, `ServiceTypeBadge`, `JobCard`, `DateNavigator`, `NotificationItem`, `Dialog`, `Skeleton`, `SkeletonJobCard`, `SkeletonProfile`, `SkeletonList`.

**Guest-app components:** `VehicleTypeCard`, `PriceSummary`, `StepIndicator`, `ExtrasSelector`, `LocationPicker`.

**Native versions to design:**
- **Buttons** — primary (filled blue), secondary (outline), tertiary/text, destructive, disabled, loading; sizes (regular/sm). Min 44px height.
- **Step indicator / progress** — funnel has 4 steps (Search → Details → Payment → Confirmation per web; mobile may collapse). Filled = done, ring = active, grey = future.
- **Location picker** — searchable cascading selector (Airport → City → Zone → Hotel). On mobile this should be a **full-screen search sheet**, not a tiny dropdown. Consider Google Maps pin-drop parity (web has a map picker).
- **Vehicle card** — vehicle photo, name, capacity (person icons × N), luggage icons, **price prominent**, selected state (`ring-2` blue + tint), per-card quote-loading state.
- **Price summary** — itemized: base + extras + total, currency-aware (`USD/EUR/GBP/EGP/SAR`).
- **Extras stepper** — quantity steppers for booster seat / baby seat / wheelchair.
- **Date & time pickers** — native pickers (`@react-native-community/datetimepicker` in use); design the trigger fields + selected display.
- **Pax stepper** — −/+ control; must respect vehicle capacity (business rule: pax ≤ capacity).
- **Status badge / service-type badge** — pill with the color tokens in §2.1.
- **Booking/Job card** — route, date/time, status, ref.
- **Notification item** — for an in-app notification list.
- **Dialog / bottom sheet** — confirmations (e.g. cancel booking), pickers.
- **Toasts** — success/error feedback (web uses `sonner`; pick a native equivalent).
- **Header / nav bar** — currently white with blue tint + back chevron. Design branded headers, including a transparent-over-hero variant for Home.

---

## 6. Content & Data Requirements

Every screen renders real API data from `https://fulvago.itourtt.cloud/api/public/*`. Shapes are in `mobile/packages/shared/src/types/index.ts`.

| Screen | Displays | Dynamic? | Empty / error states |
|---|---|---|---|
| Home | Brand, value props, trust signals (e.g. "12,400+ transfers", "4.9★") | Static + trust counts | n/a |
| Search | Location tree (`/public/locations`: Country→Airport→City→Zone→Hotel), service types, date/time, pax | Locations fetched live | Locations fail to load → `ErrorBanner` + retry |
| Choose Vehicle | Vehicle types (`/public/vehicle-types`), **live quote per vehicle** (`/public/quote`), extras, currency | Quotes fetched per vehicle, async | No vehicles → `EmptyState`; quote fails → per-card error; loading → per-card skeleton |
| Your Details | Form fields (name, email, phone, country, flight no., carrier, terminal, notes) | User input | Inline validation errors |
| Payment | Methods (`ONLINE` / `PAY_ON_ARRIVAL`), gateways (`STRIPE` / `EGYPT_BANK` / `DUBAI_BANK`) | Admin-configured availability | Gateway unavailable; payment failed |
| Confirmation | Booking ref, summary, status `CONFIRMED` | POST result | Submit fails → `ErrorBanner` + retry; don't double-submit |
| Track Booking | Ref + email form | User input | Not found / wrong email → friendly error (ownership-gated) |
| Booking Detail | Full booking, route labels, status, assignment (vehicle/driver when assigned), **evidence photos** on completed jobs, cancel action | Live | Not yet assigned → "Driver will be assigned closer to pickup"; cancelled state; no evidence yet |
| Destinations/Blog | CMS content (titles, excerpts, cover images, body) — multi-locale | Live CMS | Missing cover image → gradient placeholder (per web handoff) |

**Currency:** quotes return a currency code; format per `formatCurrency`. Support `USD, EUR, GBP, EGP, SAR`.
**Route labels:** helpers `getOriginLabel / getDestinationLabel / getRouteLabel` build human route strings — design should accommodate variable-length route text (RTL too).
**Pricing breakdown:** quote response includes a `breakdown` object — design an expandable price detail.

---

## 7. Functional Requirements (interactions / gestures / motion)

- **Pull-to-refresh** on Booking Detail and any list (a `useRefresh` hook exists).
- **Bottom sheets** for: location search, date/time, extras, payment method, cancel confirmation. Prefer sheets over full modals for funnel steps (web rule: "no heavy modals").
- **Swipe-back** navigation (iOS native edge swipe; honor on the stack).
- **Steppers** (pax, extras) with press-and-hold optional.
- **Inline validation** with gentle, specific error copy.
- **Optimistic UI with rollback** where safe (web rule) — e.g. selection states.
- **Motion:** subtle. Card press: slight scale/elevation. Step transitions: horizontal slide. Success: a tasteful confirmation animation on the Confirmation screen. **No parallax / heavy scroll-jank.**
- **Keyboard handling:** avoid covering inputs; "next field" flow on the details form.
- **Sticky CTA:** the primary action (Continue / Search / Pay) should be reachable — consider a docked bottom bar on funnel screens with the running price visible.

---

## 8. Mobile-Specific Considerations (not on web)

- **Push notifications** (Firebase Cloud Messaging is wired in `SETUP.md`). Design notification content + in-app handling for: booking confirmed, driver/vehicle assigned, pickup reminder (e.g. T-12h / T-2h), status change, flight-tracking nudge. Provide an in-app notification center (component `NotificationItem` exists).
- **Permissions priming** — pre-permission screens for notifications and location before the OS prompt.
- **Camera / gallery** — not required for guest booking v1 (evidence capture is a driver/rep feature). Guest *views* evidence photos on completed bookings. Confirm whether guests upload anything (likely no).
- **Offline states** — `OfflineBar` + `use-network` hook exist; design the offline banner and degraded states (cached booking detail, queued retry).
- **Loading skeletons** — design skeletons for funnel (vehicle list), booking detail, and lists (`Skeleton*` components exist) instead of spinners where possible.
- **Deep links / universal links** — booking confirmation links, "track this booking" from email/SMS into Booking Detail.
- **Safe areas / notches** — respect insets (`useSafeAreaInsets` already used).
- **Payment sheets** — Stripe Payment Sheet (native) for online payment; design the handoff into and back from it.
- **Maps** — Google Maps pin-drop for pickup location (web has a map picker); design the native map selector.
- **Haptics** — light haptic on key confirmations (select vehicle, booking confirmed).

---

## 9. Platform Notes (iOS vs Android, cross-platform)

Built with React Native — one design, platform-respectful where it matters.

- **Navigation pattern:** currently a **stack** (no tab bar). Recommendation: keep funnel as a stack; consider a small bottom-tab shell only if Destinations/Blog ship (Home · Trips/Bookings · Explore · More). Decide before designing chrome — **flag this as an open question for stakeholders.**
- **Headers:** iOS = centered title + back chevron; Android = left-aligned title + back arrow. The redesign should provide a branded header that reads correctly on both.
- **Date/time pickers:** iOS shows inline spinner/wheel; Android shows dialog pickers — design the **trigger field** and selected-value display, not the OS picker itself.
- **System fonts:** iOS San Francisco, Android Roboto today — unify on Inter if bundled (see §2.2).
- **Back behavior:** Android hardware/gesture back must map to in-app back; don't trap users mid-funnel without a confirm.
- **Elevation vs shadow:** Android uses elevation, iOS uses shadow — define both for cards.
- **Status bar:** already toggles light/dark content with theme.
- **RTL / Arabic:** the platform ships `en` + `ar` (`i18n/en.ts`, `i18n/ar.ts`); web supports 7 locales (`en, ru, de, pl, uk, cs, ar`). **Arabic must be fully RTL** — mirror layouts, flip directional icons (arrows/chevrons), use start/end (not left/right) spacing. Design at least one key screen in RTL to prove the system. Confirm which locales mobile v1 ships.

---

## 10. Out of Scope (web features NOT in mobile v1)

- **Admin / dashboard, dispatch, finance, reports** — entirely separate product (different apps in the monorepo). Never in the consumer app.
- **Driver / Rep / Supplier apps** — separate apps in the same monorepo (`apps/driver`, `apps/rep`, `apps/supplier`); each gets its own brief. This brief is **guest only**.
- **Full customer login / account dashboard** — web has a `B2C_CLIENT` login (password = phone number). Mobile v1 uses **booking-lookup (ref + email)** instead of authenticated accounts. A logged-in account area is **later**.
- **Online payment gateways beyond what's enabled** — the B2C web is currently **pay-on-arrival-only in some deployments**; online (Stripe/bank) is admin-toggled. Design both, but treat the available set as configurable.
- **Multi-brand theming UI** — brand color/font are runtime-themeable on web; mobile bakes the Transfera blue for v1 (keep it tokenized, but no in-app theme-switcher beyond light/dark).
- **Full 7-locale set** — confirm whether v1 ships all web locales or starts with `en` + `ar` (which already exist in mobile i18n).
- **Destinations & Blog** — recommended **later** unless stakeholders prioritize them for v1 (designed in §4 Group C so they're ready when greenlit).
- **City-to-city / 2-way transfer tabs** — these exist on web's booking widget (`ONE_WAY_TRANSFER`, `TWO_WAY_TRANSFER`, `DAY_TOUR` service types exist in types). Mobile `SearchScreen` currently exposes only Arrival/Departure. **Confirm whether v1 includes return + city-to-city + day-tour**; design should accommodate the tabbed structure if so.

---

## Appendix — Open questions for stakeholders (resolve before/with first design round)

1. **Brand mark in-app:** Transfera or iTour wordmark for the consumer app?
2. **Navigation shell:** stack-only, or bottom-tab (depends on whether Destinations/Blog ship v1)?
3. **Service types in v1:** just Arrival/Departure, or also Return (2-way), City-to-City, Day Tour?
4. **Payment:** which methods/gateways are live for the mobile launch market?
5. **Locales in v1:** `en` + `ar` only, or the full web set (`ru, de, pl, uk, cs`)?
6. **Custom font:** bundle Inter (brand consistency, +app size) or stay on system fonts?
7. **Destinations / Blog:** v1 or later?

---

*Deliverables expected from design: a mobile design-token sheet mapped to the names in §2 (so engineering can update `theme/*` 1:1), high-fidelity screens for all Group A + B screens (light **and** dark, plus one RTL proof), the component library in §5 with all states (default/pressed/disabled/loading/error/empty), app icon + splash, and notification templates. Build/run instructions to preview designs live: `mobile/SETUP.md`.*
