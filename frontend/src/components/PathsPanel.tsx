import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { api } from '../lib/api';
import { HORIZONS } from '../lib/constants';
import { formatDate } from '../lib/format';
import { useToast } from '../lib/toast';
import type { Horizon, LearningPath, Milestone, MilestoneStatus, PathKind } from '../types';
import { DeleteButton, Empty, Field, Pill, Progress } from './ui';

export function PathsPanel({ onChanged }: { onChanged: () => void }) {
  const toast = useToast();
  const [paths, setPaths] = useState<LearningPath[]>([]);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [name, setName] = useState('');
  const [kind, setKind] = useState<PathKind>('main');

  const load = useCallback(async () => {
    try {
      const [p, m] = await Promise.all([api.get<LearningPath[]>('/learning/paths'), api.get<Milestone[]>('/learning/milestones')]);
      setPaths(p);
      setMilestones(m);
    } catch (e) { toast.fail(e); }
  }, [toast]);
  useEffect(() => { void load(); }, [load]);

  async function addPath(e: FormEvent) {
    e.preventDefault();
    try { await api.post('/learning/paths', { name, kind }); setName(''); await load(); onChanged(); } catch (err) { toast.fail(err); }
  }
  async function removePath(id: string) {
    try { await api.del(`/learning/paths/${id}`); await load(); onChanged(); } catch (err) { toast.fail(err); }
  }

  return (
    <div className="stack">
      <form className="form inline panel" onSubmit={addPath}>
        <input className="grow" placeholder="New learning path (e.g. CPTS, Arabic, Rust)" value={name} onChange={(e) => setName(e.target.value)} maxLength={200} aria-label="Path name" />
        <select value={kind} onChange={(e) => setKind(e.target.value as PathKind)} aria-label="Path kind">
          <option value="main">Main</option><option value="secondary">Secondary</option>
        </select>
        <button className="primary" disabled={!name.trim()}>Add path</button>
      </form>
      {paths.length === 0 && <Empty>No paths yet. A path is a big learning goal; break it into weekly, monthly, quarterly and semester milestones.</Empty>}
      {(['main', 'secondary'] as PathKind[]).map((k) => {
        const list = paths.filter((p) => p.kind === k);
        if (!list.length) return null;
        return (
          <section key={k}>
            <h2 className="section">{k === 'main' ? 'Main paths' : 'Secondary paths'}</h2>
            <div className="stack">
              {list.map((p) => (
                <PathCard key={p.id} path={p} milestones={milestones.filter((m) => m.path_id === p.id)} reload={load} onRemove={() => void removePath(p.id)} />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

function PathCard({ path, milestones, reload, onRemove }: { path: LearningPath; milestones: Milestone[]; reload: () => Promise<void>; onRemove: () => void }) {
  const toast = useToast();
  const [title, setTitle] = useState('');
  const [horizon, setHorizon] = useState<Horizon>('weekly');
  const [due, setDue] = useState('');

  async function add(e: FormEvent) {
    e.preventDefault();
    try {
      await api.post(`/learning/paths/${path.id}/milestones`, { title, horizon, due: due || null });
      setTitle('');
      await reload();
    } catch (err) { toast.fail(err); }
  }
  async function setStatus(m: Milestone, status: MilestoneStatus) {
    try { await api.patch(`/learning/milestones/${m.id}`, { status }); await reload(); } catch (err) { toast.fail(err); }
  }
  async function remove(m: Milestone) {
    try { await api.del(`/learning/milestones/${m.id}`); await reload(); } catch (err) { toast.fail(err); }
  }

  return (
    <article className="panel">
      <header className="card-head">
        <div className="grow">
          <h3>{path.name}</h3>
          <small className="muted">
            {path.milestones_done}/{path.milestones_total} milestones{path.target_date ? ` · target ${formatDate(path.target_date)}` : ''}
          </small>
        </div>
        <DeleteButton onConfirm={onRemove} label="Delete path" />
      </header>
      <Progress value={path.progress} tone={path.progress >= 1 ? 'ok' : 'accent'} />
      <div className="horizons">
        {HORIZONS.map((h) => {
          const list = milestones.filter((m) => m.horizon === h.key);
          return (
            <section key={h.key}>
              <h4>{h.label}</h4>
              {list.length === 0 && <p className="empty small">-</p>}
              <ul className="plain">
                {list.map((m) => (
                  <li key={m.id} className={m.status === 'done' ? 'done' : ''}>
                    <input type="checkbox" checked={m.status === 'done'} aria-label={`Mark ${m.title} done`}
                      onChange={(e) => void setStatus(m, e.target.checked ? 'done' : 'todo')} />
                    <span className="grow">{m.title}{m.due && <small className="muted"> {formatDate(m.due)}</small>}</span>
                    {m.overdue && <Pill tone="late">Overdue</Pill>}
                    {m.status === 'todo' && !m.overdue && <button className="icon" title="Mark in progress" onClick={() => void setStatus(m, 'doing')}>▷</button>}
                    {m.status === 'doing' && <Pill tone="soon">Doing</Pill>}
                    <button className="icon" aria-label="Delete milestone" onClick={() => void remove(m)}>×</button>
                  </li>
                ))}
              </ul>
            </section>
          );
        })}
      </div>
      <form className="form inline" onSubmit={add}>
        <input className="grow" placeholder="Add milestone" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={300} aria-label="Milestone" />
        <select value={horizon} onChange={(e) => setHorizon(e.target.value as Horizon)} aria-label="Horizon">
          {HORIZONS.map((h) => <option key={h.key} value={h.key}>{h.label}</option>)}
        </select>
        <Field label=""><input type="date" value={due} onChange={(e) => setDue(e.target.value)} aria-label="Due date" /></Field>
        <button className="primary" disabled={!title.trim()}>Add</button>
      </form>
    </article>
  );
}
