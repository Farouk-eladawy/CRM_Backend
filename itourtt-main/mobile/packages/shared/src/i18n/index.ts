import { useCallback } from 'react';
import { en, type TranslationKeys } from './en';
import { ar } from './ar';

type Locale = 'en' | 'ar';

let currentLocale: Locale = 'en';

const translations: Record<Locale, TranslationKeys> = { en, ar };

export function setLocale(locale: Locale) {
  currentLocale = locale;
}

export function getLocale(): Locale {
  return currentLocale;
}

function getNestedValue(obj: Record<string, unknown>, path: string): string {
  const keys = path.split('.');
  let current: unknown = obj;
  for (const key of keys) {
    if (current && typeof current === 'object' && key in current) {
      current = (current as Record<string, unknown>)[key];
    } else {
      return path;
    }
  }
  return typeof current === 'string' ? current : path;
}

/** Translation function */
export function t(key: string): string {
  return getNestedValue(translations[currentLocale] as unknown as Record<string, unknown>, key);
}

/** React hook that returns the translation function */
export function useT() {
  return useCallback((key: string) => t(key), []);
}

export { en, ar };
export type { TranslationKeys };
