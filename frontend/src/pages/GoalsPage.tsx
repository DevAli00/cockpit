import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { DeleteButton, Empty, Field, Pill, Progress } from '../components/ui';
import { api } from '../lib/api';
import { formatDate, isoToday } from '../lib/format';
import { goalStatusMeta, num } from '../lib/life';
import { useToast } from '../lib/toast';
import type { Goal } from '../types';

export function GoalsPage() {
  const toast = useToast();
  const [goals, setGoals] = useState<Goal[]>([]);
  const [f, setF] = useState({ title: '', area: '', unit: '', target: '', start: isoToday(), deadline: '' });
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });

  const load = useCallback(async () => {
    try { setGoals(await api.get<Goal[]>('/goals')); } catch (e) { toast.fail(e); }
  }, [toast]);
  useEffect(() => { void load(); }, [load]);

  async function add(e: FormEvent) {
    e.preventDefault();
    try {
      await api.post('/goals', { ...f, target: f.target.replace(',', '.') });
      setF({ ...f, title: '', target: '' });
      await load();
    } catch (err) { toast.fail(err); }
  }
  async function patch(g: Goal, body: Record<string, unknown>) {
    try { await api.patch(`/goals/${g.id}`, body); await load(); } catch (err) { toast.fail(err); await load(); }
  }
  async function remove(g: Goal) {
    try { await api.del(`/goals/${g.id}`); await load(); } catch (err) { toast.fail(err); }
  }

  return (
    <>
      <header className="page-head">
        <h1>North Star</h1>
        <p className="muted">Goals with a target and a deadline. The marker shows where you should be by now if you progressed evenly; you are "behind" when you trail it by more than 10 points.</p>
      </header>
      <form className="form panel" onSubmit={add}>
        <div className="row">
          <Field label="Goal"><input value={f.title} onChange={set('title')} placeholder="PortSwigger labs, Savings, Substack posts…" required maxLength={300} /></Field>
          <Field label="Area"><input value={f.area} onChange={set('area')} placeholder="Cyber, Body, Money…" maxLength={100} /></Field>
          <Field label="Target"><input inputMode="decimal" value={f.target} onChange={set('target')} required placeholder="60" /></Field>
          <Field label="Unit"><input value={f.unit} onChange={set('unit')} placeholder="labs, €, kg" maxLength={30} /></Field>
          <Field label="Start"><input type="date" value={f.start} onChange={set('start')} required /></Field>
          <Field label="Deadline"><input type="date" value={f.deadline} onChange={set('deadline')} required /></Field>
        </div>
        <footer><span className="spacer" /><button className="primary" disabled={!f.title.trim() || !f.target}>Add goal</button></footer>
      </form>
      {goals.length === 0 && <Empty>No goals yet.</Empty>}
      <div className="stack">
        {goals.map((g) => {
          const meta = goalStatusMeta(g.status);
          return (
            <article key={g.id} className="panel goal">
              <header className="card-head">
                <div className="grow">
                  <h3>{g.title}</h3>
                  <small className="muted">{g.area && `${g.area} · `}{formatDate(g.start)} → {formatDate(g.deadline)}</small>
                </div>
                <Pill tone={meta.tone}>{meta.label}</Pill>
                <DeleteButton onConfirm={() => void remove(g)} />
              </header>
              <Progress value={g.progress} marker={g.expected} tone={g.status === 'behind' ? 'late' : g.status === 'done' ? 'ok' : 'accent'} />
              <div className="goal-foot">
                <label>
                  <input type="number" step="any" min={0} defaultValue={num(g.current)} aria-label={`Current value for ${g.title}`}
                    onBlur={(e) => { if (num(e.target.value) !== num(g.current)) void patch(g, { current: e.target.value }); }} />
                  <span> / {num(g.target)} {g.unit}</span>
                </label>
                <small className="muted">{Math.round(g.progress * 100)}% · expected {Math.round(g.expected * 100)}%</small>
              </div>
            </article>
          );
        })}
      </div>
    </>
  );
}
