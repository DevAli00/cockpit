import { formatMoney } from './format';
import type { FundKind } from '../types';

export const FUND_KINDS: { key: FundKind; label: string }[] = [
  { key: 'travel', label: 'Travel' }, { key: 'emergency', label: 'Emergency' }, { key: 'hajj', label: 'Hajj / Umrah' },
  { key: 'car', label: 'Car' }, { key: 'home', label: 'Home' }, { key: 'education', label: 'Education' },
  { key: 'gifts', label: 'Gifts & Eid' }, { key: 'charity', label: 'Charity & zakat' }, { key: 'purchase', label: 'Big purchase' },
  { key: 'wedding', label: 'Wedding' }, { key: 'other', label: 'Other' },
];

export const fundKindLabel = (k: FundKind): string => FUND_KINDS.find((x) => x.key === k)?.label ?? k;

/** One-click starting points; you set the target. */
export const FUND_PRESETS: { kind: FundKind; name: string; hint: string }[] = [
  { kind: 'emergency', name: 'Emergency fund', hint: '3–6 months of expenses' },
  { kind: 'travel', name: 'Travel fund', hint: 'trips and holidays' },
  { kind: 'hajj', name: 'Hajj / Umrah', hint: 'the journey of a lifetime' },
  { kind: 'gifts', name: 'Eid & gifts', hint: 'Eid, birthdays, weddings' },
  { kind: 'charity', name: 'Sadaqa & zakat', hint: 'set aside before you spend' },
  { kind: 'car', name: 'Car', hint: 'repairs, insurance, the next one' },
  { kind: 'education', name: 'Education', hint: 'certs, courses, books' },
  { kind: 'purchase', name: 'Big purchase', hint: 'laptop, phone, furniture' },
];

export const missingPresets = (have: { kind: FundKind }[]) =>
  FUND_PRESETS.filter((p) => !have.some((f) => f.kind === p.kind));

export function ordinal(n: number): string {
  const teen = n % 100 >= 11 && n % 100 <= 13;
  const suffix = teen ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[n % 10] ?? 'th';
  return `${n}${suffix}`;
}

/** "€200.00 every month on the 1st · 10% of every income", or '' when the fund is filled by hand. */
export function automationSummary(
  f: { monthly_amount: string | null; monthly_day: number; income_pct: string | null }, currency: string,
): string {
  const parts: string[] = [];
  if (Number(f.monthly_amount) > 0) parts.push(`${formatMoney(f.monthly_amount!, currency)} every month on the ${ordinal(f.monthly_day)}`);
  if (Number(f.income_pct) > 0) parts.push(`${Number(f.income_pct)}% of every income`);
  return parts.join(' · ');
}
