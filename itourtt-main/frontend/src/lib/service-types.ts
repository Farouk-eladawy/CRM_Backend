// ─────────────────────────────────────────────
// SERVICE TYPES (single source of truth)
// ─────────────────────────────────────────────
// Labels live in lib/i18n.ts under "serviceType.*" so they translate. Nothing
// should hard-code "ARR" / "2 Way Transfer" style text — import from here.
//
//   ARR              Arrival    وصول
//   DEP              Departure  سفر
//   DAY_TOUR         Day Tour   يومية/جولة
//   ONE_WAY_TRANSFER Going      ذهاب
//   RETURN           Return     عودة
//
// Keep in sync with backend/src/common/utils/service-type.util.ts.

import { useT } from "@/lib/i18n";

/** Offered in every dropdown, in this order. */
export const SELECTABLE_SERVICE_TYPES = [
  "ARR",
  "DEP",
  "DAY_TOUR",
  "ONE_WAY_TRANSFER",
  "RETURN",
] as const;

/**
 * Retired values. Never selectable, but still rendered — historical jobs
 * reference them.
 */
export const LEGACY_SERVICE_TYPES = ["TWO_WAY_TRANSFER", "CITY_TO_CITY"] as const;

export const ALL_SERVICE_TYPES = [
  ...SELECTABLE_SERVICE_TYPES,
  ...LEGACY_SERVICE_TYPES,
] as const;

export type ServiceType = (typeof ALL_SERVICE_TYPES)[number];

export const SERVICE_TYPE_COLORS: Record<string, string> = {
  ARR: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  DEP: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  DAY_TOUR: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  ONE_WAY_TRANSFER: "bg-teal-500/10 text-teal-400 border-teal-500/20",
  RETURN: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  TWO_WAY_TRANSFER: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
  CITY_TO_CITY: "bg-slate-500/10 text-slate-400 border-slate-500/20",
};

/** Stronger fill used by the dispatch grids. */
export const SERVICE_TYPE_COLORS_SOLID: Record<string, string> = {
  ARR: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  DEP: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  DAY_TOUR: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  ONE_WAY_TRANSFER: "bg-teal-500/20 text-teal-400 border-teal-500/30",
  RETURN: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  TWO_WAY_TRANSFER: "bg-indigo-500/20 text-indigo-400 border-indigo-500/30",
  CITY_TO_CITY: "bg-slate-500/20 text-slate-400 border-slate-500/30",
};

// Dropdowns show BOTH languages at once — "Arrival - وصول" — regardless of the
// interface language, so the picker reads the same to an English and an Arabic
// operator. Tables, badges and exports stay single-language (useServiceTypeLabel).
//
// The pair is wrapped in a LEFT-TO-RIGHT ISOLATE so it renders in the given
// order under an RTL interface too. Without it the bidi algorithm reorders the
// line to "وصول - Arrival" whenever the surrounding paragraph is RTL.
const LRI = "⁦"; // LEFT-TO-RIGHT ISOLATE
const PDI = "⁩"; // POP DIRECTIONAL ISOLATE

const bilingual = (en: string, ar: string) => `${LRI}${en} - ${ar}${PDI}`;

export const SERVICE_TYPE_DROPDOWN_LABELS: Record<string, string> = {
  ARR: bilingual("Arrival", "وصول"),
  DEP: bilingual("Departure", "سفر"),
  DAY_TOUR: bilingual("Day Tour", "يومية/جولة"),
  ONE_WAY_TRANSFER: bilingual("Going", "ذهاب"),
  RETURN: bilingual("Return", "عودة"),
  TWO_WAY_TRANSFER: bilingual("2 Way Transfer", "ذهاب وعودة"),
  CITY_TO_CITY: bilingual("City to City", "من مدينة إلى مدينة"),
};

/** Bilingual label for one service type — dropdown menus only. */
export function serviceTypeDropdownLabel(value: string | null | undefined): string {
  if (!value) return "";
  return SERVICE_TYPE_DROPDOWN_LABELS[value] ?? value;
}

/** `{ value, label }[]` for every dropdown. Locale-independent by design. */
export const SERVICE_TYPE_DROPDOWN_OPTIONS: { value: string; label: string }[] =
  SELECTABLE_SERVICE_TYPES.map((v) => ({
    value: v,
    label: SERVICE_TYPE_DROPDOWN_LABELS[v],
  }));

/**
 * Translated label for one service type. Falls back to the raw value so an
 * unknown/legacy code never renders as blank.
 */
export function useServiceTypeLabel() {
  const t = useT();
  return (value: string | null | undefined): string => {
    if (!value) return "";
    const label = t(`serviceType.${value}`);
    return label === `serviceType.${value}` ? value : label;
  };
}

