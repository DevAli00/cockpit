import type { EntryType, NoteKind, Period, ProjectStatus, TaskColumn } from '../types';

export const PROJECT_STATUSES: ProjectStatus[] = ['Not started', 'In progress', 'On hold', 'Done'];

export const COLUMNS: { key: TaskColumn; label: string; dot: string }[] = [
  { key: 'todo', label: 'To do', dot: '#9aa0ae' },
  { key: 'ongoing', label: 'In progress', dot: '#e9a23b' },
  { key: 'blocked', label: 'Blocked', dot: '#e0525a' },
  { key: 'done', label: 'Done', dot: '#2fa565' },
];

export const CATEGORIES: Record<EntryType, string[]> = {
  revenue: ['Services', 'Subscriptions / retainers', 'Products', 'Other income'],
  direct: ['Subcontracting', 'Project materials', 'Client licences'],
  opex: ['Software & SaaS', 'Marketing', 'Rent & office', 'Travel', 'Bank fees', 'Taxes & charges', 'Training', 'Other expense'],
};

/** Personal money uses two of the three types: revenue = income, opex = expenses. */
export const PERSONAL_CATEGORIES: Record<'revenue' | 'opex', string[]> = {
  revenue: ['Salary', 'Freelance', 'Bonus', 'Refunds', 'Gifts', 'Investment income', 'Other income'],
  opex: [
    'Housing', 'Groceries', 'Transport', 'Utilities & phone', 'Health', 'Subscriptions', 'Eating out',
    'Shopping', 'Travel', 'Sport', 'Education & books', 'Family', 'Charity & zakat', 'Gifts', 'Other expense',
  ],
};

export const TYPE_LABEL: Record<EntryType, string> = {
  revenue: 'Revenue', direct: 'Direct cost', opex: 'Operating expense',
};

export const CURRENCIES = ['EUR', 'USD', 'GBP', 'CAD', 'CHF', 'MAD'];

export const NOTE_KINDS: { key: NoteKind; label: string }[] = [
  { key: 'note', label: 'Note' }, { key: 'call', label: 'Call' }, { key: 'decision', label: 'Decision' },
  { key: 'feedback', label: 'Feedback' }, { key: 'email', label: 'Email' },
];

export const PERIODS: { key: Period; label: string }[] = [
  { key: 'month', label: 'This month' }, { key: '3m', label: '3 months' },
  { key: '12m', label: '12 months' }, { key: 'all', label: 'All time' },
];

export const CLIENT_COLORS = ['#2f6fde', '#2fa565', '#e9a23b', '#e0525a', '#8b5cf6', '#0ea5a4', '#d9488a', '#64748b'];

export const HORIZONS: { key: import('../types').Horizon; label: string }[] = [
  { key: 'weekly', label: 'Weekly' }, { key: 'monthly', label: 'Monthly' },
  { key: 'quarterly', label: 'Quarterly' }, { key: 'semester', label: 'Semester' },
];

export const ITEM_KINDS: { key: import('../types').ItemKind; label: string }[] = [
  { key: 'book', label: 'Book' }, { key: 'article', label: 'Article' }, { key: 'writing', label: 'Writing' },
  { key: 'course', label: 'Course' }, { key: 'lab', label: 'Lab' }, { key: 'video', label: 'Video' },
  { key: 'paper', label: 'Paper' }, { key: 'other', label: 'Other' },
];

export const TRIP_STATUSES: import('../types').TripStatus[] = ['idea', 'planned', 'booked', 'done'];
export const TRIP_ITEM_KINDS: import('../types').TripItemKind[] = ['flight', 'stay', 'activity', 'todo', 'other'];
