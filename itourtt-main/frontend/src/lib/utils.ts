import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

/**
 * The business operates exclusively in Egypt. All operational dates/times
 * (flight arrival/departure, pickup, meeting times, dispatch windows) are
 * Africa/Cairo and MUST render in Cairo regardless of the viewer's device
 * timezone — otherwise a rep/admin on a UTC device sees a 14:30 flight as
 * 11:30 and the IN PLACE window appears shifted.
 */
export const APP_TZ = "Africa/Cairo";

/** Format the HH:mm (24h) portion of an instant in Cairo time. */
export function formatTimeCairo(value: string | Date | null | undefined): string | null {
  if (!value) return null;
  const d = typeof value === "string" ? new Date(value) : value;
  if (isNaN(d.getTime())) return null;
  return d.toLocaleTimeString("en-GB", {
    timeZone: APP_TZ,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

/** Return YYYY-MM-DD for an instant as it falls on the calendar in Cairo. */
export function dateStrCairo(value: string | Date): string {
  const d = typeof value === "string" ? new Date(value) : value;
  if (isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-CA", { timeZone: APP_TZ }); // en-CA => YYYY-MM-DD
}

/**
 * Interpret a wall-clock date (YYYY-MM-DD) + time (HH:mm) as Africa/Cairo and
 * return the corresponding UTC instant as an ISO string. Use when sending a
 * user-entered Cairo time to the API, so it never depends on the device timezone.
 */
export function cairoWallclockToISO(dateStr: string, timeStr: string): string {
  const naiveUTC = Date.parse(`${dateStr}T${timeStr}:00Z`);
  if (isNaN(naiveUTC)) return new Date(`${dateStr}T${timeStr}:00`).toISOString();
  // Find Cairo's UTC offset at that instant, then back it out.
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: APP_TZ,
    hourCycle: "h23",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).formatToParts(new Date(naiveUTC));
  const m: Record<string, string> = {};
  for (const p of parts) m[p.type] = p.value;
  const asCairo = Date.UTC(+m.year, +m.month - 1, +m.day, +m.hour, +m.minute, +m.second);
  const offset = asCairo - naiveUTC;
  return new Date(naiveUTC - offset).toISOString();
}

/** Return YYYY-MM-DD in local timezone (safe for API date params) */
export function localDateStr(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** Format a date as dd-MMM-yy (e.g. 07-Feb-26) */
export function formatDate(value: string | Date): string {
  const d = typeof value === "string" ? new Date(value) : value;
  if (isNaN(d.getTime())) return "\u2014";
  const dd = String(d.getDate()).padStart(2, "0");
  const mmm = MONTHS[d.getMonth()];
  const yy = String(d.getFullYear()).slice(2);
  return `${dd}-${mmm}-${yy}`;
}
