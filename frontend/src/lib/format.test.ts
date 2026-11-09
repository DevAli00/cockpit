import { describe, expect, it } from 'vitest';
import { beforeIdAt, formatMoney, isoToday, monthLabel, relativeDue } from './format';

describe('formatMoney', () => {
  it('formats strings from the API with the currency', () => {
    expect(formatMoney('1234.5', 'EUR')).toMatch(/1[\s ,.]?234[.,]50/);
    expect(formatMoney('1234.5', 'EUR')).toContain('€');
  });
  it('treats garbage as zero rather than NaN', () => {
    expect(formatMoney('abc', 'EUR')).not.toContain('NaN');
  });
  it('falls back for an unknown currency code', () => {
    expect(() => formatMoney('1', 'ZZZ')).not.toThrow();
  });
});

describe('beforeIdAt', () => {
  const ids = ['a', 'b', 'c'];
  it('returns the id currently at the drop index', () => {
    expect(beforeIdAt(ids, 0, 'x')).toBe('a');
    expect(beforeIdAt(ids, 2, 'x')).toBe('c');
  });
  it('returns null when dropping at the end', () => {
    expect(beforeIdAt(ids, 3, 'x')).toBeNull();
  });
  it('skips the dragged card itself', () => {
    expect(beforeIdAt(ids, 1, 'b')).toBe('c');
    expect(beforeIdAt(ids, 2, 'c')).toBeNull();
  });
});

describe('dates', () => {
  it('isoToday is yyyy-mm-dd in local time', () => {
    expect(isoToday(new Date(2026, 2, 5, 23, 59))).toBe('2026-03-05');
  });
  it('monthLabel renders yyyy-mm', () => {
    expect(monthLabel('2026-03')).toMatch(/Mar/);
  });
  it('relativeDue flags overdue, today and soon', () => {
    const today = new Date(2026, 2, 10);
    expect(relativeDue('2026-03-09', today)).toEqual({ text: 'Overdue', tone: 'late' });
    expect(relativeDue('2026-03-10', today)).toEqual({ text: 'Today', tone: 'soon' });
    expect(relativeDue('2026-03-12', today).tone).toBe('soon');
    expect(relativeDue('2026-04-01', today).tone).toBe('ok');
  });
});
