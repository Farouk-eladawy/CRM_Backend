const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** Format a date as dd-MMM-yy (e.g. 07-Feb-26) */
export function formatDate(value: string | Date): string {
  const d = typeof value === 'string' ? new Date(value) : value;
  if (isNaN(d.getTime())) return '\u2014';
  const dd = String(d.getDate()).padStart(2, '0');
  const mmm = MONTHS[d.getMonth()];
  const yy = String(d.getFullYear()).slice(2);
  return `${dd}-${mmm}-${yy}`;
}

/** Format a date as YYYY-MM-DD for API calls */
export function toApiDate(date: Date): string {
  return date.toISOString().split('T')[0];
}

/** Format time from ISO string as HH:mm */
export function formatTime(isoString: string | null | undefined): string {
  if (!isoString) return '\u2014';
  const d = new Date(isoString);
  if (isNaN(d.getTime())) return '\u2014';
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

/** Get today's date as YYYY-MM-DD */
export function today(): string {
  return toApiDate(new Date());
}

/** Add/subtract days from a date string (YYYY-MM-DD) */
export function addDays(dateStr: string, days: number): string {
  const d = new Date(dateStr + 'T00:00:00');
  d.setDate(d.getDate() + days);
  return toApiDate(d);
}
