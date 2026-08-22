import { formatCurrency } from '../../src/utils/currency';
import type { Currency } from '../../src/types';

describe('formatCurrency', () => {
  describe('EGP currency', () => {
    it('formats with EGP symbol by default', () => {
      expect(formatCurrency(100)).toBe('EGP 100.00');
    });

    it('formats with EGP symbol when explicitly passed', () => {
      expect(formatCurrency(100, 'EGP')).toBe('EGP 100.00');
    });
  });

  describe('USD currency', () => {
    it('formats with $ symbol', () => {
      expect(formatCurrency(250, 'USD')).toBe('$ 250.00');
    });
  });

  describe('EUR currency', () => {
    it('formats with euro symbol', () => {
      expect(formatCurrency(150, 'EUR')).toBe('\u20AC 150.00');
    });
  });

  describe('GBP currency', () => {
    it('formats with pound symbol', () => {
      expect(formatCurrency(300, 'GBP')).toBe('\u00A3 300.00');
    });
  });

  describe('SAR currency', () => {
    it('formats with SAR text symbol', () => {
      expect(formatCurrency(500, 'SAR')).toBe('SAR 500.00');
    });
  });

  describe('edge cases', () => {
    it('handles zero amount', () => {
      expect(formatCurrency(0, 'EGP')).toBe('EGP 0.00');
    });

    it('handles negative amounts', () => {
      const result = formatCurrency(-100, 'USD');
      expect(result).toContain('100.00');
      expect(result).toContain('$');
    });

    it('handles large numbers with comma grouping', () => {
      const result = formatCurrency(1000000, 'EGP');
      expect(result).toBe('EGP 1,000,000.00');
    });

    it('handles decimal amounts', () => {
      expect(formatCurrency(99.99, 'USD')).toBe('$ 99.99');
    });

    it('rounds to two decimal places', () => {
      expect(formatCurrency(10.999, 'EGP')).toBe('EGP 11.00');
    });

    it('pads to two decimal places when needed', () => {
      expect(formatCurrency(50.5, 'EUR')).toBe('\u20AC 50.50');
    });

    it('handles unknown currency by using currency code as symbol', () => {
      // Cast to bypass TS type checking for testing unknown currencies
      expect(formatCurrency(100, 'XYZ' as Currency)).toBe('XYZ 100.00');
    });

    it('handles very small fractional amounts', () => {
      expect(formatCurrency(0.01, 'EGP')).toBe('EGP 0.01');
    });

    it('formats thousands correctly', () => {
      expect(formatCurrency(1500.75, 'GBP')).toBe('\u00A3 1,500.75');
    });
  });
});
