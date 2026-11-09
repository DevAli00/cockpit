import { describe, expect, it } from 'vitest';
import { FUND_KINDS, FUND_PRESETS, automationSummary, fundKindLabel, missingPresets, ordinal } from './funds';

describe('fund kinds', () => {
  it('has a label for every kind the API accepts', () => {
    expect(FUND_KINDS.map((k) => k.key)).toEqual([
      'travel', 'emergency', 'hajj', 'car', 'home', 'education', 'gifts', 'charity', 'purchase', 'wedding', 'other',
    ]);
    expect(fundKindLabel('hajj')).toBe('Hajj / Umrah');
  });
});

describe('missingPresets', () => {
  it('offers only presets whose kind you do not have yet', () => {
    const left = missingPresets([{ kind: 'travel' }, { kind: 'emergency' }]);
    expect(left.some((p) => p.kind === 'travel')).toBe(false);
    expect(left.some((p) => p.kind === 'hajj')).toBe(true);
    expect(missingPresets([]).length).toBe(FUND_PRESETS.length);
  });
});

describe('automationSummary', () => {
  const base = { monthly_amount: null, monthly_day: 1, income_pct: null };
  it('describes how a fund fills itself', () => {
    expect(automationSummary({ ...base, monthly_amount: '200.00', monthly_day: 1 }, 'EUR')).toBe('€200.00 every month on the 1st');
    expect(automationSummary({ ...base, income_pct: '10.00' }, 'EUR')).toBe('10% of every income');
    expect(automationSummary({ ...base, monthly_amount: '50', monthly_day: 22, income_pct: '2.5' }, 'EUR'))
      .toBe('€50.00 every month on the 22nd · 2.5% of every income');
    expect(automationSummary({ ...base, monthly_amount: '0' }, 'EUR')).toBe('');
  });
  it('uses the right ordinal suffix', () => {
    expect([1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 28].map(ordinal)).toEqual(
      ['1st', '2nd', '3rd', '4th', '11th', '12th', '13th', '21st', '22nd', '23rd', '28th'],
    );
  });
});
