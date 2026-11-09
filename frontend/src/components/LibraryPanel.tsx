import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { api } from '../lib/api';
import { ITEM_KINDS } from '../lib/constants';
import { formatDate } from '../lib/format';
import { itemStatusLabel } from '../lib/life';
import { useToast } from '../lib/toast';
import type { ItemKind, ItemStatus, LearningItem, LearningPath } from '../types';
import { DeleteButton, Empty, Progress } from './ui';

const TABS: { key: 'all' | ItemKind; label: string }[] = [
  { key: 'all', label: 'All' }, { key: 'book', label: 'Books' }, { key: 'article', label: 'Articles' },
  { key: 'writing', label: 'Writing' }, { key: 'lab', label: 'Labs' }, { key: 'course', label: 'Courses' },
];
const STATUSES: ItemStatus[] = ['backlog', 'in_progress', 'done', 'dropped'];

export function LibraryPanel({ onChanged }: { onChanged: () => void }) {
  const toast = useToast();
  const [tab, setTab] = useState<'all' | ItemKind>('all');
  const [items, setItems] = useState<LearningItem[]>([]);
  const [paths, setPaths] = useState<LearningPath[]>([]);
  const [title, setTitle] = useState('');
  const [kind, setKind] = useState<ItemKind>('book');
  const [total, setTotal] = useState('');
  const [pathId, setPathId] = useState('');

  const load = useCallback(async () => {
    try {
      const [i, p] = await Promise.all([api.get<LearningItem[]>('/learning/items'), api.get<LearningPath[]>('/learning/paths')]);
      setItems(i);
      setPaths(p);
    } catch (e) { toast.fail(e); }
  }, [toast]);
  useEffect(() => { void load(); }, [load]);

  async function add(e: FormEvent) {
    e.preventDefault();
    try {
      await api.post('/learning/items', { title, kind, path_id: pathId || null, progress_total: total ? Number(total) : null });
      setTitle(''); setTotal('');
      await load(); onChanged();
    } catch (err) { toast.fail(err); }
  }
  async function patch(i: LearningItem, body: Record<string, unknown>) {
    try { await api.patch(`/learning/items/${i.id}`, body); await load(); onChanged(); } catch (err) { toast.fail(err); }
  }
  async function remove(i: LearningItem) {
    try { await api.del(`/learning/items/${i.id}`); await load(); onChanged(); } catch (err) { toast.fail(err); }
  }

  const shown = items.filter((i) => tab === 'all' || i.kind === tab);
  const unit = (k: ItemKind) => (k === 'book' ? 'pages/chapters' : k === 'lab' || k === 'course' ? 'steps' : 'units');

  return (
    <div className="stack">
      <form className="form inline panel" onSubmit={add}>
        <select value={kind} onChange={(e) => setKind(e.target.value as ItemKind)} aria-label="Kind">
          {ITEM_KINDS.map((k) => <option key={k.key} value={k.key}>{k.label}</option>)}
        </select>
        <input className="grow" placeholder="Title (a book to read, an article to write, a lab to finish…)" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={300} aria-label="Title" />
        <input type="number" min={1} placeholder={`Total ${unit(kind)}`} value={total} onChange={(e) => setTotal(e.target.value)} aria-label="Total" style={{ width: '9rem' }} />
        <select value={pathId} onChange={(e) => setPathId(e.target.value)} aria-label="Path">
          <option value="">No path</option>
          {paths.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <button className="primary" disabled={!title.trim()}>Add</button>
      </form>

      <div className="seg" role="tablist">
        {TABS.map((t) => (
          <button key={t.key} role="tab" aria-selected={t.key === tab} className={t.key === tab ? 'on' : ''} onClick={() => setTab(t.key)}>{t.label}</button>
        ))}
      </div>

      {shown.length === 0 && <Empty>Nothing here yet.</Empty>}
      <ul className="items">
        {shown.map((i) => (
          <li key={i.id} className="panel">
            <div className="item-main">
              <span className="tag">{ITEM_KINDS.find((k) => k.key === i.kind)?.label}</span>
              <strong className="grow">
                {i.url ? <a href={i.url} target="_blank" rel="noopener noreferrer">{i.title}</a> : i.title}
                {i.author && <small className="muted"> {i.author}</small>}
              </strong>
              <select value={i.status} onChange={(e) => void patch(i, { status: e.target.value })} aria-label="Status">
                {STATUSES.map((s) => <option key={s} value={s}>{itemStatusLabel(i.kind, s)}</option>)}
              </select>
              <DeleteButton onConfirm={() => void remove(i)} />
            </div>
            {i.progress_total !== null && (
              <div className="item-progress">
                <Progress value={(i.percent ?? 0) / 100} tone={i.status === 'done' ? 'ok' : 'accent'} />
                <label>
                  <input type="number" min={0} max={i.progress_total} defaultValue={i.progress_current} aria-label="Progress"
                    onBlur={(e) => { const v = Number(e.target.value); if (v !== i.progress_current) void patch(i, { progress_current: v }); }} />
                  / {i.progress_total}
                </label>
              </div>
            )}
            <div className="item-foot">
              {i.status === 'done' && <span className="stars" aria-label="Rating">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button key={n} className={`icon star${(i.rating ?? 0) >= n ? ' on' : ''}`} aria-label={`${n} stars`} onClick={() => void patch(i, { rating: n })}>★</button>
                ))}
              </span>}
              {i.finished && <small className="muted">finished {formatDate(i.finished)}</small>}
              {!i.finished && i.started && <small className="muted">started {formatDate(i.started)}</small>}
              {i.path_id && <small className="muted">{paths.find((p) => p.id === i.path_id)?.name}</small>}
            </div>
            <textarea className="note-input" rows={1} placeholder="Notes, key takeaways…" defaultValue={i.notes} maxLength={20000} aria-label="Notes"
              onBlur={(e) => { if (e.target.value !== i.notes) void patch(i, { notes: e.target.value }); }} />
          </li>
        ))}
      </ul>
    </div>
  );
}
