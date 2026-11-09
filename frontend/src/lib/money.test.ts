import { describe, expect, it } from 'vitest';
import { ACCOUNT_TYPES, accountKind, chartPoints, greeting, moneyLabels, signedMoney } from './money';

describe('accounts', () => {
  it('knows which types are debts', () => {
    expect(accountKind('loan')).toBe('liability');
    expect(accountKind('credit_card')).toBe('liability');
    expect(accountKind('savings')).toBe('asset');
    expect(ACCOUNT_TYPES.filter((t) => t.kind === 'liability').map((t) => t.key)).toEqual(['loan', 'mortgage', 'credit_card', 'other_debt']);
  });
});

describe('signedMoney', () => {
  it('always shows the sign of a change', () => {
    expect(signedMoney('900', 'EUR')).toMatch(/^\+€900\.00$/);
    expect(signedMoney('-50.5', 'EUR')).toMatch(/^−€50\.50$/);
    expect(signedMoney('0', 'EUR')).toMatch(/^€0\.00$/);
  });
});

describe('chartPoints', () => {
  it('maps values into the box, highest at the top', () => {
    expect(chartPoints([0, 50, 100], 200, 100)).toBe('0,100 100,50 200,0');
  });
  it('draws a flat line through the middle when all values are equal', () => {
    expect(chartPoints([5, 5], 100, 40)).toBe('0,20 100,20');
  });
  it('handles one point and no points', () => {
    expect(chartPoints([7], 100, 40)).toBe('0,20 100,20');
    expect(chartPoints([], 100, 40)).toBe('');
  });
});

describe('moneyLabels', () => {
  it('speaks personal finance when personal', () => {
    expect(moneyLabels('personal')).toMatchObject({ revenue: 'Income', opex: 'Expenses', net: 'Saved', netRate: 'Savings rate' });
    expect(moneyLabels('business').revenue).toBe('Revenue');
  });
});

describe('greeting', () => {
  it.each([[6, 'Good morning'], [13, 'Good afternoon'], [19, 'Good evening'], [2, 'Good night']])('%sh', (h, g) => {
    expect(greeting(new Date(2026, 10, 1, h))).toBe(g);
  });
});
