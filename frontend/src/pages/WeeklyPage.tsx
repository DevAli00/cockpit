import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { DeleteButton, Empty, Field, Pill } from '../components/ui';
import { api } from '../lib/api';
import { formatDate } from '../lib/format';
import { mondayOf, num, shiftWeek } from '../lib/life';
import { useToast } from '../lib/toast';
import type { Metric, WeekCheck, WeeklySummary } from '../types';

const STATUS_TONE = { on_target: 'ok', close: 'soon', below: 'late' } as const;
const STATUS_LABEL = { on_target: 'On target', close: 'Close', below: 'Below' } as const;

export function WeeklyPage() {
  const toast = useToast();
  const thisMonday = mondayOf(new Date());
  const [week, setWeek] = useState(thisMonday);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [checks, setChecks] = useState<WeekCheck[]>([]);
  const [summary, setSummary] = useState<WeeklySummary | null>(null);

  const load = useCallback(async () => {
    try {
      const [m, c, s] = await Promise.all([
        api.get<Metric[]>('/weekly/metrics'), api.get<WeekCheck[]>('/weekly/checks'), api.get<WeeklySummary>('/weekly/summary'),
      ]);
      setMetrics(m); setChecks(c); setSummary(s);
    } catch (e) { toast.fail(e); }
  }, [toast]);
  useEffect(() => { void load(); }, [load]);

  const current = checks.find((c) => c.week_start === week) ?? null;

  return (
    <>
      <header className="page-head">
        <h1>Weekly check</h1>
        <p className="muted">Twenty minutes every Sunday: log the week against your targets, name one focus for next week.</p>
      </header>

      {summary?.last?.focus_next && (
        <section className="panel focus">
          <small className="muted">#1 focus (from your last check)</small>
          <p><strong>{summary.last.focus_next}</strong></p>
        </section>
      )}

      <div className="grid2">
        <section className="panel">
          <header className="card-head">
            <h2 className="section grow">Week of {formatDate(week)}</h2>
            <button className="small" onClick={() => setWeek(shiftWeek(week, -1))} aria-label="Previous week">←</button>
            <button className="small" disabled={week >= thisMonday} onClick={() => setWeek(shiftWeek(week, 1))} aria-label="Next week">→</button>
          </header>
          {metrics.length === 0 ? <Empty>Add your first metric on the right (for example "Focus hours", target 16).</Empty> : (
            <CheckForm key={`${week}:${current?.id ?? 'new'}:${metrics.length}`} week={week} metrics={metrics} check={current} onSaved={load} />
          )}
        </section>

        <div className="stack">
          <section className="panel">
            <h2 className="section">Averages vs targets</h2>
            {summary && summary.weeks_logged > 0 && summary.consistency !== null && (
              <p className="muted">{summary.weeks_logged} weeks logged · {Math.round(summary.consistency * 100)}% minimum-viable weeks</p>
            )}
            <table><tbody>
              {summary?.metrics.map((m) => (
                <tr key={m.metric_id}>
                  <td>{m.name}<small className="muted block">target {num(m.target)} {m.unit}</small></td>
                  <td className="num">{m.average ?? '-'}</td>
                  <td className="act">{m.status && <Pill tone={STATUS_TONE[m.status]}>{STATUS_LABEL[m.status]}</Pill>}</td>
                </tr>
              ))}
            </tbody></table>
          </section>
          <MetricsEditor metrics={metrics} reload={load} />
        </div>
      </div>

      <section className="panel">
        <h2 className="section">History</h2>
        {checks.length === 0 && <Empty>No weeks logged yet.</Empty>}
        <table><tbody>
          {checks.map((c) => (
            <tr key={c.id} className="clickable" onClick={() => setWeek(c.week_start)}>
              <td>{formatDate(c.week_start)}{c.focus_next && <small className="muted block">→ {c.focus_next}</small>}</td>
              <td className="num">{c.score !== null ? `${Math.round(c.score * 100)}%` : '-'}</td>
              <td className="act">
                {c.min_viable === true && <Pill tone="ok">Min viable</Pill>}
                {c.min_viable === false && <Pill tone="late">Below minimum</Pill>}
                {c.burnout && <Pill tone="late">Deload</Pill>}
              </td>
            </tr>
          ))}
        </tbody></table>
      </section>
    </>
  );
}

function CheckForm({ week, metrics, check, onSaved }: { week: string; metrics: Metric[]; check: WeekCheck | null; onSaved: () => Promise<void> }) {
  const toast = useToast();
  const [values, setValues] = useState<Record<string, string>>(
    Object.fromEntries(metrics.map((m) => [m.id, check?.values[m.id] !== undefined ? String(num(check.values[m.id])) : ''])),
  );
  const [energy, setEnergy] = useState(check?.energy ? String(check.energy) : '');
  const [win, setWin] = useState(check?.win ?? '');
  const [blocker, setBlocker] = useState(check?.blocker ?? '');
  const [focus, setFocus] = useState(check?.focus_next ?? '');

  async function save(e: FormEvent) {
    e.preventDefault();
    const filled = Object.fromEntries(Object.entries(values).filter(([, v]) => v.trim() !== '').map(([k, v]) => [k, v.replace(',', '.')]));
    try {
      await api.put(`/weekly/checks/${week}`, { energy: energy ? Number(energy) : null, win, blocker, focus_next: focus, values: filled });
      await onSaved();
      toast.ok('Week saved');
    } catch (err) { toast.fail(err); }
  }

  return (
    <form className="form" onSubmit={save}>
      <div className="row">
        {metrics.map((m) => (
          <Field key={m.id} label={`${m.name}${m.unit ? ` (${m.unit})` : ''} · target ${num(m.target)}`}>
            <input inputMode="decimal" value={values[m.id] ?? ''} onChange={(e) => setValues({ ...values, [m.id]: e.target.value })} placeholder="-" />
          </Field>
        ))}
      </div>
      <Field label="Energy (1 drained - 5 great)">
        <select value={energy} onChange={(e) => setEnergy(e.target.value)}>
          <option value="">-</option>{[1, 2, 3, 4, 5].map((n) => <option key={n}>{n}</option>)}
        </select>
      </Field>
      <Field label="Win of the week"><textarea rows={2} value={win} onChange={(e) => setWin(e.target.value)} maxLength={20000} /></Field>
      <Field label="Blocker"><textarea rows={2} value={blocker} onChange={(e) => setBlocker(e.target.value)} maxLength={20000} /></Field>
      <Field label="#1 focus next week"><input value={focus} onChange={(e) => setFocus(e.target.value)} maxLength={20000} /></Field>
      {check && (
        <p className="row">
          {check.score !== null && <Pill tone={check.score >= 0.8 ? 'ok' : check.score >= 0.5 ? 'soon' : 'late'}>Score {Math.round(check.score * 100)}%</Pill>}
          {check.min_viable === true && <Pill tone="ok">Minimum viable week</Pill>}
          {check.min_viable === false && <Pill tone="late">Below minimum</Pill>}
          {check.burnout && <Pill tone="late">Low energy: deload, protect sleep</Pill>}
        </p>
      )}
      <footer><span className="spacer" /><button className="primary">Save week</button></footer>
    </form>
  );
}

function MetricsEditor({ metrics, reload }: { metrics: Metric[]; reload: () => Promise<void> }) {
  const toast = useToast();
  const [f, setF] = useState({ name: '', unit: '', target: '', min_viable: '' });
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });

  async function add(e: FormEvent) {
    e.preventDefault();
    try {
      await api.post('/weekly/metrics', { name: f.name, unit: f.unit, target: f.target.replace(',', '.'), min_viable: f.min_viable ? f.min_viable.replace(',', '.') : null });
      setF({ name: '', unit: '', target: '', min_viable: '' });
      await reload();
    } catch (err) { toast.fail(err); }
  }
  async function patch(m: Metric, body: Record<string, unknown>) {
    try { await api.patch(`/weekly/metrics/${m.id}`, body); await reload(); } catch (err) { toast.fail(err); await reload(); }
  }
  async function remove(m: Metric) {
    try { await api.del(`/weekly/metrics/${m.id}`); await reload(); } catch (err) { toast.fail(err); }
  }

  return (
    <section className="panel">
      <h2 className="section">Metrics you track</h2>
      <p className="muted">"Min" is the minimum-viable level for a bad week. Deleting a metric deletes its history.</p>
      <ul className="plain">
        {metrics.map((m) => (
          <li key={m.id}>
            <span className="grow">{m.name} <small className="muted">{m.unit}</small></span>
            <label className="mini">target <input inputMode="decimal" defaultValue={num(m.target)} aria-label={`Target for ${m.name}`}
              onBlur={(e) => { if (num(e.target.value) !== num(m.target) && num(e.target.value) > 0) void patch(m, { target: e.target.value }); }} /></label>
            <label className="mini">min <input inputMode="decimal" defaultValue={m.min_viable === null ? '' : num(m.min_viable)} aria-label={`Minimum for ${m.name}`}
              onBlur={(e) => { const v = e.target.value; if (v !== (m.min_viable === null ? '' : String(num(m.min_viable)))) void patch(m, { min_viable: v === '' ? null : v }); }} /></label>
            <DeleteButton onConfirm={() => void remove(m)} />
          </li>
        ))}
      </ul>
      <form className="form inline" onSubmit={add}>
        <input className="grow" placeholder="Focus hours" value={f.name} onChange={set('name')} maxLength={100} aria-label="Metric name" />
        <input placeholder="unit" value={f.unit} onChange={set('unit')} style={{ width: '5rem' }} maxLength={30} aria-label="Unit" />
        <input placeholder="target" value={f.target} onChange={set('target')} style={{ width: '5rem' }} inputMode="decimal" aria-label="Target" />
        <input placeholder="min" value={f.min_viable} onChange={set('min_viable')} style={{ width: '4rem' }} inputMode="decimal" aria-label="Minimum viable" />
        <button className="primary" disabled={!f.name.trim() || !f.target}>Add</button>
      </form>
    </section>
  );
}
