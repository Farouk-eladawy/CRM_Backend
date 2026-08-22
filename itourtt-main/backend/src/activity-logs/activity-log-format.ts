/**
 * Human-readable formatting for Activity Log details.
 *
 * The audit interceptor stores raw request bodies / record snapshots, where
 * values are often UUIDs (e.g. `originZoneId`) or short codes (e.g. `ARR`).
 * These helpers turn field keys into friendly labels and resolve codes — while
 * UUID references are resolved against the DB by the service (see MODEL_DISPLAY).
 */

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Friendly window/screen name for an audit `entity` string. Sub-resources use
 *  dot notation (e.g. "Agent.PriceList") and render as "Agents › Price List". */
const WINDOW_LABELS: Record<string, string> = {
  TrafficJob: 'Traffic Jobs',
  Agent: 'Agents',
  Customer: 'Customers',
  Supplier: 'Suppliers',
  Driver: 'Drivers',
  Rep: 'Reps',
  Vehicle: 'Vehicles',
  VehicleType: 'Vehicle Types',
  Location: 'Locations',
  Dispatch: 'Dispatch Console',
  Finance: 'Finance',
  Invoice: 'Invoices',
  JobLock: 'Job Locks',
  Permission: 'Permissions',
  Settings: 'Settings',
  Report: 'Reports',
  Whatsapp: 'WhatsApp',
  ActivityLog: 'Activity Log',
  User: 'Users',
};

export function windowLabel(entity: string): string {
  return entity
    .split('.')
    .map((part) => WINDOW_LABELS[part] ?? humanizeField(part))
    .join(' › ');
}

/** Audit `entity` name → Prisma model, so a log's entityId (a UUID) can be
 *  resolved to a readable reference (e.g. a TrafficJob's internal ref). */
const ENTITY_TO_MODEL: Record<string, string> = {
  TrafficJob: 'trafficJob',
  Agent: 'agent',
  Customer: 'customer',
  Supplier: 'supplier',
  Driver: 'driver',
  Rep: 'rep',
  Vehicle: 'vehicle',
  VehicleType: 'vehicleType',
  User: 'user',
};

/** The Prisma model an audit entity's record id points to, if resolvable. */
export function entityModel(entity: string): string | null {
  return ENTITY_TO_MODEL[entity.split('.')[0]] ?? null;
}

/** Explicit field-label overrides where the auto-humanizer reads poorly. */
const FIELD_LABELS: Record<string, string> = {
  paxCount: 'Passengers',
  adultCount: 'Adults',
  childCount: 'Children',
  internalRef: 'Internal Ref',
  agentRef: 'Agent Ref',
  pickUpTime: 'Pick-up Time',
  flight: 'Flight',
  bookingStatus: 'Booking Status',
  status: 'Status',
  isActive: 'Active',
  legalName: 'Legal Name',
  tradeName: 'Trade Name',
  plateNumber: 'Plate Number',
};

/** field key (lower-cased) → Prisma model the UUID value points to. */
const FIELD_TO_MODEL: Record<string, string> = {
  agentid: 'agent',
  customerid: 'customer',
  supplierid: 'supplier',
  driverid: 'driver',
  repid: 'rep',
  vehicleid: 'vehicle',
  vehicletypeid: 'vehicleType',
  zoneid: 'zone',
  originzoneid: 'zone',
  destinationzoneid: 'zone',
  fromzoneid: 'zone',
  tozoneid: 'zone',
  pickupzoneid: 'zone',
  dropoffzoneid: 'zone',
  hotelid: 'hotel',
  originhotelid: 'hotel',
  destinationhotelid: 'hotel',
  airportid: 'airport',
  originairportid: 'airport',
  destinationairportid: 'airport',
  cityid: 'city',
  countryid: 'country',
  userid: 'user',
  createdbyid: 'user',
  updatedbyid: 'user',
  changedbyid: 'user',
  submittedbyid: 'user',
  trafficjobid: 'trafficJob',
  jobid: 'trafficJob',
};

/** A selected row passed to a model's display formatter. */
type DisplayRow = Record<string, string | null | undefined>;

/** Per-model lookup config used by the service to batch-resolve UUIDs → names. */
export const MODEL_DISPLAY: Record<
  string,
  { select: Record<string, true>; format: (r: DisplayRow) => string }
> = {
  agent: {
    select: { tradeName: true, legalName: true },
    format: (r) => r.tradeName || r.legalName || '',
  },
  customer: {
    select: { tradeName: true, legalName: true },
    format: (r) => r.tradeName || r.legalName || '',
  },
  supplier: {
    select: { tradeName: true, legalName: true },
    format: (r) => r.tradeName || r.legalName || '',
  },
  driver: { select: { name: true }, format: (r) => r.name || '' },
  rep: { select: { name: true }, format: (r) => r.name || '' },
  vehicle: {
    select: { plateNumber: true },
    format: (r) => r.plateNumber || '',
  },
  vehicleType: { select: { name: true }, format: (r) => r.name || '' },
  zone: { select: { name: true }, format: (r) => r.name || '' },
  hotel: { select: { name: true }, format: (r) => r.name || '' },
  airport: {
    select: { name: true, code: true },
    format: (r) => `${r.name ?? ''} (${r.code ?? ''})`,
  },
  city: { select: { name: true }, format: (r) => r.name || '' },
  country: { select: { name: true }, format: (r) => r.name || '' },
  user: {
    select: { name: true, email: true },
    format: (r) => r.name || r.email || '',
  },
  trafficJob: {
    select: { internalRef: true },
    format: (r) => r.internalRef || '',
  },
};

/** Short-code → readable label, keyed by field name. */
const CODE_LABELS: Record<string, Record<string, string>> = {
  serviceType: { ARR: 'Arrival', DEP: 'Departure', CITY: 'City Tour' },
  paymentMethod: { PAY_ON_ARRIVAL: 'Pay on Arrival', ONLINE: 'Online Payment' },
};

/** camelCase / snake_case field key → "Title Case" label, trailing "Id" dropped. */
export function humanizeField(key: string): string {
  if (FIELD_LABELS[key]) return FIELD_LABELS[key];
  return key
    .replace(/Id$/, '')
    .replace(/_/g, ' ')
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** The model a field's UUID value references, if any. */
export function fieldModel(key: string): string | null {
  return FIELD_TO_MODEL[key.toLowerCase()] ?? null;
}

/** Whether a value looks like a resolvable UUID. */
export function isUuid(v: unknown): v is string {
  return typeof v === 'string' && UUID_RE.test(v);
}

/**
 * Render a single value as a readable string.
 * @param lookups map of `${model}:${uuid}` → resolved display name.
 */
export function formatValue(
  key: string,
  value: unknown,
  lookups: Record<string, string>,
): string {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';

  const codes = CODE_LABELS[key];
  if (codes && typeof value === 'string' && codes[value]) return codes[value];

  const model = fieldModel(key);
  if (model && isUuid(value)) {
    return lookups[`${model}:${value}`] ?? value;
  }

  if (Array.isArray(value)) {
    return value.map((v) => formatValue(key, v, lookups)).join(', ');
  }
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value as string | number);
}

/** Fields that are noise in a user-facing view. */
const HIDDEN_FIELDS = new Set([
  'id',
  'createdAt',
  'updatedAt',
  'deletedAt',
  'password',
  'passwordHash',
  'refreshToken',
]);

export function isHiddenField(key: string): boolean {
  return HIDDEN_FIELDS.has(key);
}
