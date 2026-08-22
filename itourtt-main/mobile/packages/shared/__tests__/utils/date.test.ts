import { formatDate, toApiDate, formatTime, today, addDays } from '../../src/utils/date';

describe('date utils', () => {
  describe('formatDate', () => {
    it('formats a date string as dd-MMM-yy', () => {
      expect(formatDate('2026-02-07')).toBe('07-Feb-26');
    });

    it('formats a Date object as dd-MMM-yy', () => {
      const d = new Date(2026, 0, 15); // Jan 15, 2026
      expect(formatDate(d)).toBe('15-Jan-26');
    });

    it('formats all months correctly', () => {
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      months.forEach((month, index) => {
        const d = new Date(2025, index, 10);
        expect(formatDate(d)).toContain(month);
      });
    });

    it('pads single-digit days with leading zero', () => {
      expect(formatDate('2026-03-05')).toBe('05-Mar-26');
    });

    it('returns em dash for invalid date string', () => {
      expect(formatDate('not-a-date')).toBe('\u2014');
    });

    it('returns em dash for empty string', () => {
      expect(formatDate('')).toBe('\u2014');
    });

    it('handles end-of-year dates', () => {
      expect(formatDate('2025-12-31')).toBe('31-Dec-25');
    });

    it('handles start-of-year dates', () => {
      expect(formatDate('2026-01-01')).toBe('01-Jan-26');
    });
  });

  describe('toApiDate', () => {
    it('returns YYYY-MM-DD format', () => {
      const d = new Date('2026-02-20T15:30:00Z');
      expect(toApiDate(d)).toBe('2026-02-20');
    });

    it('strips time information', () => {
      const d = new Date('2026-06-15T23:59:59Z');
      const result = toApiDate(d);
      expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    });

    it('handles midnight correctly', () => {
      const d = new Date('2026-01-01T00:00:00Z');
      expect(toApiDate(d)).toBe('2026-01-01');
    });
  });

  describe('formatTime', () => {
    it('formats ISO string as HH:mm', () => {
      // Create a date at a known local time
      const d = new Date(2026, 1, 20, 14, 30, 0);
      const result = formatTime(d.toISOString());
      expect(result).toBe('14:30');
    });

    it('pads single-digit hours and minutes', () => {
      const d = new Date(2026, 1, 20, 5, 3, 0);
      const result = formatTime(d.toISOString());
      expect(result).toBe('05:03');
    });

    it('returns em dash for null', () => {
      expect(formatTime(null)).toBe('\u2014');
    });

    it('returns em dash for undefined', () => {
      expect(formatTime(undefined)).toBe('\u2014');
    });

    it('returns em dash for empty string', () => {
      expect(formatTime('')).toBe('\u2014');
    });

    it('returns em dash for invalid date string', () => {
      expect(formatTime('not-a-time')).toBe('\u2014');
    });

    it('handles midnight (00:00)', () => {
      const d = new Date(2026, 1, 20, 0, 0, 0);
      const result = formatTime(d.toISOString());
      expect(result).toBe('00:00');
    });
  });

  describe('today', () => {
    it('returns a string in YYYY-MM-DD format', () => {
      const result = today();
      expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    });

    it('matches the current date', () => {
      const now = new Date();
      const expected = now.toISOString().split('T')[0];
      expect(today()).toBe(expected);
    });
  });

  describe('addDays', () => {
    it('adds days correctly', () => {
      expect(addDays('2026-02-20', 1)).toBe('2026-02-21');
    });

    it('subtracts days with negative number', () => {
      expect(addDays('2026-02-20', -1)).toBe('2026-02-19');
    });

    it('handles month rollover when adding', () => {
      expect(addDays('2026-01-31', 1)).toBe('2026-02-01');
    });

    it('handles month rollover when subtracting', () => {
      expect(addDays('2026-03-01', -1)).toBe('2026-02-28');
    });

    it('handles year rollover', () => {
      expect(addDays('2025-12-31', 1)).toBe('2026-01-01');
    });

    it('handles adding zero days', () => {
      expect(addDays('2026-02-20', 0)).toBe('2026-02-20');
    });

    it('handles adding many days', () => {
      expect(addDays('2026-01-01', 365)).toBe('2027-01-01');
    });

    it('handles leap year', () => {
      // 2028 is a leap year
      expect(addDays('2028-02-28', 1)).toBe('2028-02-29');
      expect(addDays('2028-02-29', 1)).toBe('2028-03-01');
    });
  });
});
