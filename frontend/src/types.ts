export type ProjectStatus = 'Not started' | 'In progress' | 'On hold' | 'Done';
export type TaskColumn = 'todo' | 'ongoing' | 'blocked' | 'done';
export type EntryType = 'revenue' | 'direct' | 'opex';
export type Frequency = 'monthly' | 'yearly';
export type NoteKind = 'note' | 'call' | 'decision' | 'feedback' | 'email';
export type Period = 'month' | '3m' | '12m' | 'all';

/** Money arrives as decimal strings so nothing is lost to float rounding. */
export type Money = string;

export interface Profile { name: string; email: string; company: string; currency: string; show_business: boolean }
export interface Client { id: string; name: string; color: string }
export interface Brief { context: string; goal: string; deliverables: string; out: string }
export interface Project {
  id: string; name: string; client_id: string | null; start: string | null; deadline: string | null;
  status: ProjectStatus; position: number; brief: Brief;
}
export interface Note { id: string; project_id: string; date: string; kind: NoteKind; body: string; created_at: string }
export interface Task {
  id: string; title: string; col: TaskColumn; client_id: string | null; project_id: string | null;
  due: string | null; note: string; position: number; done_at: string | null; created_at: string;
}
export interface Entry {
  scope: Scope; fund_id: string | null; id: string; date: string; label: string; type: EntryType; category: string; amount: Money; project_id: string | null;
}
export interface Recurring {
  scope: Scope; fund_id: string | null; id: string; label: string; type: EntryType; category: string; amount: Money; frequency: Frequency;
  start: string; end: string | null; project_id: string | null;
}
export interface Txn extends Omit<Entry, 'id' | 'scope'> { id: string; recurring_id: string | null }
export interface Totals {
  revenue: Money; direct: Money; opex: Money; gross: Money; net: Money; gross_rate: Money; net_rate: Money;
}
export interface FinanceSummary {
  period: Period; start: string | null; totals: Totals;
  by_category: { type: EntryType; category: string; amount: Money }[];
  by_month: { month: string; revenue: Money; costs: Money }[];
  transactions: Txn[];
  funds: { to_funds: Money; from_funds: Money; left_over: Money } | null;
}
export interface SearchHit {
  kind: 'client' | 'project' | 'note' | 'task' | 'entry' | 'recurring' | 'path' | 'milestone' | 'item' | 'trip' | 'goal' | 'account' | 'fund';
  id: string; title: string; subtitle: string; project_id: string | null;
}

// --- life cockpit ---------------------------------------------------------------------------
export type PathKind = 'main' | 'secondary';
export type PathStatus = 'active' | 'paused' | 'done';
export type Horizon = 'weekly' | 'monthly' | 'quarterly' | 'semester';
export type MilestoneStatus = 'todo' | 'doing' | 'done' | 'slipped';
export type ItemKind = 'book' | 'article' | 'course' | 'lab' | 'video' | 'paper' | 'writing' | 'other';
export type ItemStatus = 'backlog' | 'in_progress' | 'done' | 'dropped';
export type TripStatus = 'idea' | 'planned' | 'booked' | 'done';
export type TripItemKind = 'flight' | 'stay' | 'activity' | 'todo' | 'other';
export type GoalStatus = 'done' | 'starting' | 'on_track' | 'behind';

export interface LearningPath {
  id: string; name: string; kind: PathKind; description: string; status: PathStatus;
  start: string | null; target_date: string | null;
  milestones_total: number; milestones_done: number; progress: number;
}
export interface Milestone {
  id: string; path_id: string; title: string; horizon: Horizon; due: string | null;
  status: MilestoneStatus; notes: string; overdue: boolean;
}
export interface LearningItem {
  id: string; kind: ItemKind; title: string; author: string; url: string; path_id: string | null;
  status: ItemStatus; progress_current: number; progress_total: number | null; rating: number | null;
  started: string | null; finished: string | null; notes: string; percent: number | null;
}
export interface LearningOverview {
  done_by_kind: Record<string, number>; done_this_year: number; in_progress: number; backlog: number;
}
export interface TripItem {
  id: string; trip_id: string; kind: TripItemKind; label: string; date: string | null; cost: Money | null; done: boolean;
}
export interface Trip {
  id: string; destination: string; start: string | null; end: string | null; status: TripStatus;
  budget: Money | null; notes: string; spent: Money; budget_left: Money | null; days_until: number | null;
  items_total: number; items_done: number;
}
export interface TripDetail extends Trip { items: TripItem[] }
export interface Goal {
  id: string; title: string; area: string; unit: string; target: Money; current: Money;
  start: string; deadline: string; progress: number; expected: number; status: GoalStatus;
}
export interface Metric { id: string; name: string; unit: string; target: Money; min_viable: Money | null }
export interface WeekCheck {
  id: string; week_start: string; energy: number | null; win: string; blocker: string; focus_next: string;
  values: Record<string, Money>; score: number | null; min_viable: boolean | null; burnout: boolean;
}
export interface WeeklySummary {
  weeks_logged: number; consistency: number | null; last: WeekCheck | null;
  metrics: { metric_id: string; name: string; unit: string; target: Money; average: string | null; status: 'on_target' | 'close' | 'below' | null }[];
}

// --- personal money ---------------------------------------------------------------------------
export type Scope = 'business' | 'personal';
export type AccountType =
  | 'cash' | 'savings' | 'investment' | 'retirement' | 'crypto' | 'property' | 'vehicle' | 'other_asset'
  | 'loan' | 'mortgage' | 'credit_card' | 'other_debt';
export interface Account {
  id: string; name: string; type: AccountType; institution: string; notes: string;
  kind: 'asset' | 'liability'; balance: Money | null; as_of: string | null;
}
export interface NetWorthSummary {
  assets: Money; liabilities: Money; net: Money; change_30d: Money | null; stale_accounts: number;
  by_type: { type: AccountType; kind: 'asset' | 'liability'; amount: Money }[];
  history: { at: string; assets: Money; liabilities: Money; net: Money }[];
}

export type FundKind =
  | 'travel' | 'emergency' | 'hajj' | 'car' | 'home' | 'education' | 'gifts' | 'charity' | 'purchase' | 'wedding' | 'other';
export interface Fund {
  id: string; name: string; kind: FundKind; target: Money; deadline: string | null; trip_id: string | null; notes: string;
  balance: Money; remaining: Money; progress: number; funded: boolean;
  monthly_needed: Money | null; weekly_needed: Money | null; contributions: number;
  monthly_amount: Money | null; monthly_day: number; income_pct: Money | null; auto_start: string | null;
}
export interface FundMovement {
  date: string; amount: Money; source: 'manual' | 'monthly' | 'income_share' | 'expense' | 'income'; label: string; ref: string | null;
}
export interface Contribution { id: string; fund_id: string; date: string; amount: Money; note: string }
