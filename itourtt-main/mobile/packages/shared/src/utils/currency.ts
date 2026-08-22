import type { Currency } from '../types';

const currencySymbols: Record<Currency, string> = {
  EGP: 'EGP',
  USD: '$',
  EUR: '\u20AC',
  GBP: '\u00A3',
  SAR: 'SAR',
};

export function formatCurrency(amount: number, currency: Currency = 'EGP'): string {
  const symbol = currencySymbols[currency] || currency;
  return `${symbol} ${amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
