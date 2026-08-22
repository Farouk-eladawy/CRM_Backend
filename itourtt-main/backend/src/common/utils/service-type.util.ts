// ─────────────────────────────────────────────
// SERVICE TYPES (single source of truth)
// ─────────────────────────────────────────────
// Display names are business-facing and were set by the operator. Keep this in
// sync with frontend/src/lib/service-types.ts and
// mobile/packages/shared/src/i18n/{en,ar}.ts.
//
//   ARR              Arrival    وصول
//   DEP              Departure  سفر
//   DAY_TOUR         Day Tour   يومية/جولة
//   ONE_WAY_TRANSFER Going      ذهاب
//   RETURN           Return     عودة

/** Offered in every dropdown, in this order. */
export const SELECTABLE_SERVICE_TYPES = [
  'ARR',
  'DEP',
  'DAY_TOUR',
  'ONE_WAY_TRANSFER',
  'RETURN',
] as const;

/**
 * Retired values. Never selectable, but still accepted by filters and still
 * rendered, because historical rows reference them and a Postgres enum value
 * cannot be dropped while in use.
 */
export const LEGACY_SERVICE_TYPES = ['TWO_WAY_TRANSFER', 'CITY_TO_CITY'] as const;

export const ALL_SERVICE_TYPES = [
  ...SELECTABLE_SERVICE_TYPES,
  ...LEGACY_SERVICE_TYPES,
] as const;

export type SelectableServiceType = (typeof SELECTABLE_SERVICE_TYPES)[number];

const LABELS_EN: Record<string, string> = {
  ARR: 'Arrival',
  DEP: 'Departure',
  DAY_TOUR: 'Day Tour',
  ONE_WAY_TRANSFER: 'Going',
  RETURN: 'Return',
  TWO_WAY_TRANSFER: '2 Way Transfer',
  CITY_TO_CITY: 'City to City',
};

const LABELS_AR: Record<string, string> = {
  ARR: 'وصول',
  DEP: 'سفر',
  DAY_TOUR: 'يومية/جولة',
  ONE_WAY_TRANSFER: 'ذهاب',
  RETURN: 'عودة',
  TWO_WAY_TRANSFER: 'ذهاب وعودة',
  CITY_TO_CITY: 'من مدينة إلى مدينة',
};

/** Human-readable service type for exports, reports and notifications. */
export function serviceTypeLabel(
  value: string | null | undefined,
  locale: 'en' | 'ar' = 'en',
): string {
  if (!value) return '';
  const labels = locale === 'ar' ? LABELS_AR : LABELS_EN;
  return labels[value] ?? value;
}

/** `[value, label]` pairs for pickers and template dropdowns. */
export const SERVICE_TYPE_LABEL_PAIRS: [string, string][] =
  SELECTABLE_SERVICE_TYPES.map((v) => [v, LABELS_EN[v]]);

/** Non-airport service types — the "excursions & transfers" grouping. */
export const NON_FLIGHT_SERVICE_TYPES = [
  'DAY_TOUR',
  'ONE_WAY_TRANSFER',
  'RETURN',
  'TWO_WAY_TRANSFER',
  'CITY_TO_CITY',
] as const;
