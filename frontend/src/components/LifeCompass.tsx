import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import { countdown, goalStatusMeta } from '../lib/life';
import { useData } from '../lib/data';
import { formatMoney } from '../lib/format';
import { signedMoney } from '../lib/money';
import { num } from '../lib/life';
import type { Fund, Goal, NetWorthSummary, Trip, WeeklySummary } from '../types';
import { Pill } from './ui';

/** The "where am I, what's next" strip on the Overview. Fails quietly: it is a convenience, not core. */
export function LifeCompass() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [trip, setTrip] = useState<Trip | null>(null);
  const [week, setWeek] = useState<WeeklySummary | null>(null);
  const [worth, setWorth] = useState<NetWorthSummary | null>(null);
  const [funds, setFunds] = useState<Fund[]>([]);
  const { profile } = useData();

  useEffect(() => {
    void Promise.allSettled([api.get<Goal[]>('/goals'), api.get<Trip[]>('/trips'), api.get<WeeklySummary>('/weekly/summary'), api.get<NetWorthSummary>('/networth/summary'), api.get<Fund[]>('/funds')]).then(([g, t, w, n, f]) => {
      if (f.status === 'fulfilled') setFunds(f.value);
      if (n.status === 'fulfilled' && n.value.history.length) setWorth(n.value);
      if (g.status === 'fulfilled') setGoals(g.value);
      if (t.status === 'fulfilled') setTrip(t.value.find((x) => x.days_until !== null && x.days_until >= 0 && x.status !== 'done') ?? null);
      if (w.status === 'fulfilled') setWeek(w.value);
    });
  }, []);

  const open = goals.filter((g) => g.status !== 'done');
  const behind = open.filter((g) => g.status === 'behind');
  const focus = week?.last?.focus_next;
  if (!goals.length && !trip && !focus && !worth && !funds.length) return null;
  const saved = funds.reduce((a, x) => a + num(x.balance), 0);
  const targets = funds.reduce((a, x) => a + num(x.target), 0);

  return (
    <div className="kpis compass">
      {focus && <Link to="/weekly" className="kpi"><small>#1 focus</small><strong>{focus}</strong></Link>}
      {goals.length > 0 && (
        <Link to="/goals" className="kpi">
          <small>North Star</small>
          <strong>{open.length - behind.length}/{open.length} on track</strong>
          {behind.length > 0 && <Pill tone="late">{behind.length} behind: {behind.slice(0, 2).map((g) => g.title).join(', ')}</Pill>}
          {open.length > 0 && behind.length === 0 && <Pill tone={goalStatusMeta('on_track').tone}>All good</Pill>}
        </Link>
      )}
      {worth && (
        <Link to="/money" className="kpi">
          <small>Net worth</small>
          <strong>{formatMoney(worth.net, profile.currency)}</strong>
          {worth.change_30d !== null && <em className={Number(worth.change_30d) >= 0 ? 'pos' : 'neg'}>{signedMoney(worth.change_30d, profile.currency)} / 30 days</em>}
        </Link>
      )}
      {funds.length > 0 && (
        <Link to="/money" className="kpi">
          <small>Funds</small>
          <strong>{formatMoney(saved, profile.currency)}</strong>
          <em>of {formatMoney(targets, profile.currency)} across {funds.length} fund{funds.length === 1 ? '' : 's'}</em>
        </Link>
      )}
      {trip && <Link to={`/trips/${trip.id}`} className="kpi"><small>Next trip</small><strong>{trip.destination}</strong><em>{countdown(trip.days_until)}</em></Link>}
    </div>
  );
}
