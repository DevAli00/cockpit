import type { GoalStatus, ItemKind, ItemStatus } from '../types';
import { isoToday } from './format';

const parse = (iso: string): Date => {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y!, m! - 1, d);
};

/** Monday of the week containing `d`, as yyyy-mm-dd (local time). */
export function mondayOf(d: Date): string {
  const offset = (d.getDay() + 6) % 7; // Sunday -> 6
  return isoToday(new Date(d.getFullYear(), d.getMonth(), d.getDate() - offset));
}

/** Whole-week shift using calendar arithmetic, so DST changes cannot move it off a Monday. */
export function shiftWeek(iso: string, weeks: number): string {
  const d = parse(iso);
  return isoToday(new Date(d.getFullYear(), d.getMonth(), d.getDate() + 7 * weeks));
}

export function countdown(days: number | null): string {
  if (days === null) return '';
  if (days === 0) return 'today';
  if (days === 1) return 'tomorrow';
  if (days === -1) return 'yesterday';
  return days > 0 ? `in ${days} days` : `${-days} days ago`;
}

const GENERIC: Record<ItemStatus, string> = { backlog: 'Backlog', in_progress: 'In progress', done: 'Done', dropped: 'Dropped' };
const LABELS: Partial<Record<ItemKind, Record<ItemStatus, string>>> = {
  book: { backlog: 'To read', in_progress: 'Reading', done: 'Read', dropped: 'Dropped' },
  article: { backlog: 'To read', in_progress: 'Reading', done: 'Read', dropped: 'Dropped' },
  paper: { backlog: 'To read', in_progress: 'Reading', done: 'Read', dropped: 'Dropped' },
  writing: { backlog: 'Idea', in_progress: 'Draft', done: 'Published', dropped: 'Dropped' },
  lab: { backlog: 'To do', in_progress: 'Doing', done: 'Done', dropped: 'Dropped' },
  course: { backlog: 'To do', in_progress: 'Learning', done: 'Completed', dropped: 'Dropped' },
  video: { backlog: 'To watch', in_progress: 'Watching', done: 'Watched', dropped: 'Dropped' },
};
export const itemStatusLabel = (kind: ItemKind, status: ItemStatus): string => (LABELS[kind] ?? GENERIC)[status];

export function goalStatusMeta(s: GoalStatus): { label: string; tone: 'ok' | 'soon' | 'late' } {
  switch (s) {
    case 'done': return { label: 'Done', tone: 'ok' };
    case 'on_track': return { label: 'On track', tone: 'ok' };
    case 'behind': return { label: 'Behind', tone: 'late' };
    default: return { label: 'Starting', tone: 'soon' };
  }
}

export const num = (v: string | number | null | undefined): number => {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
};
