import type { AccountType, Scope } from '../types';
import { formatMoney } from './format';

export const ACCOUNT_TYPES: { key: AccountType; label: string; kind: 'asset' | 'liability' }[] = [
  { key: 'cash', label: 'Current account / cash', kind: 'asset' },
  { key: 'savings', label: 'Savings', kind: 'asset' },
  { key: 'investment', label: 'Investments', kind: 'asset' },
  { key: 'retirement', label: 'Retirement', kind: 'asset' },
  { key: 'crypto', label: 'Crypto', kind: 'asset' },
  { key: 'property', label: 'Property', kind: 'asset' },
  { key: 'vehicle', label: 'Vehicle', kind: 'asset' },
  { key: 'other_asset', label: 'Other asset', kind: 'asset' },
  { key: 'loan', label: 'Loan', kind: 'liability' },
  { key: 'mortgage', label: 'Mortgage', kind: 'liability' },
  { key: 'credit_card', label: 'Credit card', kind: 'liability' },
  { key: 'other_debt', label: 'Other debt', kind: 'liability' },
];

export const accountKind = (t: AccountType): 'asset' | 'liability' =>
  ACCOUNT_TYPES.find((x) => x.key === t)?.kind ?? 'asset';
export const accountLabel = (t: AccountType): string => ACCOUNT_TYPES.find((x) => x.key === t)?.label ?? t;

/** A change with an explicit sign: +€900.00 / −€50.50 / €0.00. */
export function signedMoney(amount: string | number, currency: string): string {
  const n = Number(amount);
  const abs = formatMoney(Math.abs(Number.isFinite(n) ? n : 0), currency);
  return n > 0 ? `+${abs}` : n < 0 ? `−${abs}` : abs;
}

/** SVG polyline points for a series in a w×h box; the highest value sits at the top. */
export function chartPoints(values: number[], w: number, h: number): string {
  if (!values.length) return '';
  const series = values.length === 1 ? [values[0]!, values[0]!] : values;
  const min = Math.min(...series);
  const span = Math.max(...series) - min;
  const step = w / (series.length - 1);
  return series
    .map((v, i) => `${Math.round(i * step * 100) / 100},${span === 0 ? h / 2 : Math.round((h - ((v - min) / span) * h) * 100) / 100}`)
    .join(' ');
}

export function moneyLabels(scope: Scope) {
  return scope === 'personal'
    ? { revenue: 'Income', direct: 'Direct costs', opex: 'Expenses', gross: 'Gross', net: 'Saved', netRate: 'Savings rate', costs: 'Spent' }
    : { revenue: 'Revenue', direct: 'Direct costs', opex: 'Overheads', gross: 'Gross margin', net: 'Net margin', netRate: 'Net margin', costs: 'Costs' };
}

export function greeting(d: Date = new Date()): string {
  const h = d.getHours();
  if (h < 5) return 'Good night';
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}
