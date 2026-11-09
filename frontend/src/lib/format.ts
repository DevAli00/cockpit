const LOCALE = 'en-GB';

export function formatMoney(amount: string | number, currency: string): string {
  const n = Number(amount);
  const value = Number.isFinite(n) ? n : 0;
  try {
    return new Intl.NumberFormat(LOCALE, { style: 'currency', currency }).format(value);
  } catch {
    return `${value.toFixed(2)} ${currency}`;
  }
}

export const formatPct = (v: string | number): string => `${Number(v || 0).toFixed(0)}%`;

export function isoToday(d: Date = new Date()): string {
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export function formatDate(iso: string | null): string {
  if (!iso) return '';
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y!, m! - 1, d).toLocaleDateString(LOCALE, { day: 'numeric', month: 'short', year: 'numeric' });
}

export function monthLabel(key: string): string {
  const [y, m] = key.split('-').map(Number);
  return new Date(y!, m! - 1, 1).toLocaleDateString(LOCALE, { month: 'short', year: 'numeric' });
}

export function relativeDue(iso: string, today: Date = new Date()): { text: string; tone: 'late' | 'soon' | 'ok' } {
  const t = isoToday(today);
  if (iso < t) return { text: 'Overdue', tone: 'late' };
  if (iso === t) return { text: 'Today', tone: 'soon' };
  const soon = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 3);
  return { text: formatDate(iso), tone: iso <= isoToday(soon) ? 'soon' : 'ok' };
}

/**
 * The card a dropped task should go in front of, given the column's ordered ids and the drop
 * index (null = end of column). The dragged card is ignored so a drop next to itself is stable.
 */
export function beforeIdAt(ids: readonly string[], index: number, draggedId: string): string | null {
  for (let i = index; i < ids.length; i++) {
    if (ids[i] !== draggedId) return ids[i]!;
  }
  return null;
}
