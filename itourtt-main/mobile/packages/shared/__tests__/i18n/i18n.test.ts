import { t, setLocale, getLocale } from '../../src/i18n';
import { en } from '../../src/i18n/en';
import { ar } from '../../src/i18n/ar';

describe('i18n', () => {
  beforeEach(() => {
    // Reset to English before each test
    setLocale('en');
  });

  describe('t() - translation function', () => {
    it('resolves top-level dot-notation keys', () => {
      expect(t('common.save')).toBe('Save');
    });

    it('resolves nested dot-notation keys', () => {
      expect(t('auth.login')).toBe('Sign In');
    });

    it('resolves deeply nested keys', () => {
      expect(t('status.PENDING')).toBe('Pending');
    });

    it('returns the key itself when translation is missing', () => {
      expect(t('nonexistent.key')).toBe('nonexistent.key');
    });

    it('returns the key when a partial path is given', () => {
      // 'common' resolves to an object, not a string
      expect(t('common')).toBe('common');
    });

    it('returns key for deeply nested nonexistent path', () => {
      expect(t('a.b.c.d.e')).toBe('a.b.c.d.e');
    });

    it('translates job statuses', () => {
      expect(t('status.ASSIGNED')).toBe('Assigned');
      expect(t('status.IN_PROGRESS')).toBe('In Progress');
      expect(t('status.COMPLETED')).toBe('Completed');
      expect(t('status.CANCELLED')).toBe('Cancelled');
      expect(t('status.NO_SHOW')).toBe('No Show');
    });

    it('translates service types', () => {
      expect(t('serviceType.ARR')).toBe('Arrival');
      expect(t('serviceType.DEP')).toBe('Departure');
      expect(t('serviceType.DAY_TOUR')).toBe('Day Tour');
      expect(t('serviceType.ONE_WAY_TRANSFER')).toBe('Going');
      expect(t('serviceType.RETURN')).toBe('Return');
    });
  });

  describe('setLocale / getLocale', () => {
    it('defaults to English', () => {
      expect(getLocale()).toBe('en');
    });

    it('changes locale to Arabic', () => {
      setLocale('ar');
      expect(getLocale()).toBe('ar');
    });

    it('changes locale back to English', () => {
      setLocale('ar');
      setLocale('en');
      expect(getLocale()).toBe('en');
    });

    it('uses Arabic translations after setting locale to ar', () => {
      setLocale('ar');
      const result = t('common.save');
      expect(result).toBe(ar.common.save);
      expect(result).not.toBe(en.common.save);
    });

    it('restores English translations after switching back', () => {
      setLocale('ar');
      setLocale('en');
      expect(t('common.save')).toBe('Save');
    });
  });

  describe('translation key parity between en and ar', () => {
    function getLeafKeys(obj: Record<string, unknown>, prefix = ''): string[] {
      const keys: string[] = [];
      for (const key of Object.keys(obj)) {
        const fullKey = prefix ? `${prefix}.${key}` : key;
        const value = obj[key];
        if (value && typeof value === 'object' && !Array.isArray(value)) {
          keys.push(...getLeafKeys(value as Record<string, unknown>, fullKey));
        } else {
          keys.push(fullKey);
        }
      }
      return keys;
    }

    it('English and Arabic have the same top-level sections', () => {
      const enSections = Object.keys(en).sort();
      const arSections = Object.keys(ar).sort();
      expect(enSections).toEqual(arSections);
    });

    it('English and Arabic have the same leaf keys', () => {
      const enKeys = getLeafKeys(en as unknown as Record<string, unknown>).sort();
      const arKeys = getLeafKeys(ar as unknown as Record<string, unknown>).sort();
      expect(enKeys).toEqual(arKeys);
    });

    it('critical keys exist in both languages', () => {
      const criticalKeys = [
        'common.save',
        'common.cancel',
        'common.loading',
        'auth.login',
        'auth.logout',
        'auth.password',
        'status.PENDING',
        'status.COMPLETED',
        'jobs.myJobs',
        'driver.startTrip',
        'driver.completeTrip',
      ];

      criticalKeys.forEach((key) => {
        setLocale('en');
        const enVal = t(key);
        expect(enVal).not.toBe(key); // Should resolve to a real translation

        setLocale('ar');
        const arVal = t(key);
        expect(arVal).not.toBe(key); // Should resolve to a real translation
      });
    });
  });
});
