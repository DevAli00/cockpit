import { describe, expect, it } from 'vitest';
import { countdown, goalStatusMeta, itemStatusLabel, mondayOf, shiftWeek } from './life';

describe('mondayOf', () => {
  it('returns the Monday of the week, local time', () => {
    expect(mondayOf(new Date(2026, 9, 4))).toBe('2026-09-28'); // a Sunday
    expect(mondayOf(new Date(2026, 8, 28))).toBe('2026-09-28'); // already Monday
    expect(mondayOf(new Date(2026, 9, 1))).toBe('2026-09-28'); // Thursday
  });
  it('handles month and year boundaries', () => {
    expect(mondayOf(new Date(2027, 0, 1))).toBe('2026-12-28');
  });
});

describe('shiftWeek', () => {
  it('moves by whole weeks across DST changes', () => {
    expect(shiftWeek('2026-10-19', 1)).toBe('2026-10-26'); // clocks change 25 Oct
    expect(shiftWeek('2026-10-26', -1)).toBe('2026-10-19');
    expect(shiftWeek('2026-12-28', 1)).toBe('2027-01-04');
  });
});

describe('countdown', () => {
  it.each([
    [null, ''],
    [0, 'today'],
    [1, 'tomorrow'],
    [20, 'in 20 days'],
    [-1, 'yesterday'],
    [-5, '5 days ago'],
  ])('%s -> %s', (days, text) => expect(countdown(days)).toBe(text));
});

describe('labels', () => {
  it('uses wording that fits the kind of item', () => {
    expect(itemStatusLabel('writing', 'in_progress')).toBe('Draft');
    expect(itemStatusLabel('writing', 'done')).toBe('Published');
    expect(itemStatusLabel('book', 'in_progress')).toBe('Reading');
    expect(itemStatusLabel('book', 'done')).toBe('Read');
    expect(itemStatusLabel('lab', 'backlog')).toBe('To do');
    expect(itemStatusLabel('video', 'dropped')).toBe('Dropped');
  });
  it('maps goal status to a label and tone', () => {
    expect(goalStatusMeta('on_track')).toEqual({ label: 'On track', tone: 'ok' });
    expect(goalStatusMeta('behind').tone).toBe('late');
    expect(goalStatusMeta('done').tone).toBe('ok');
    expect(goalStatusMeta('starting').tone).toBe('soon');
  });
});
