import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import type { SearchHit } from '../types';

const ICON: Record<SearchHit['kind'], string> = {
  client: 'Client', project: 'Project', note: 'Note', task: 'Task', entry: 'Transaction', recurring: 'Recurring',
  path: 'Path', milestone: 'Milestone', item: 'Library', trip: 'Trip', goal: 'Goal', account: 'Account', fund: 'Fund',
};

function target(h: SearchHit): string {
  if (h.project_id && (h.kind === 'project' || h.kind === 'note')) return `/projects/${h.project_id}`;
  if (h.kind === 'task') return '/';
  if (h.kind === 'path' || h.kind === 'milestone' || h.kind === 'item') return '/learning';
  if (h.kind === 'trip') return `/trips/${h.id}`;
  if (h.kind === 'goal') return '/goals';
  if (h.kind === 'account' || h.kind === 'fund') return '/money';
  return '/data';
}

/** Ctrl/Cmd+K: search everything stored in Cockpit. */
export function SearchPalette({ onClose }: { onClose: () => void }) {
  const nav = useNavigate();
  const [q, setQ] = useState('');
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [active, setActive] = useState(0);
  const seq = useRef(0);

  useEffect(() => {
    const term = q.trim();
    if (term.length < 2) { setHits([]); return; }
    const mine = ++seq.current;
    const t = window.setTimeout(() => {
      api.get<SearchHit[]>(`/search?q=${encodeURIComponent(term)}`)
        .then((r) => { if (mine === seq.current) { setHits(r); setActive(0); } })
        .catch(() => { if (mine === seq.current) setHits([]); });
    }, 150);
    return () => window.clearTimeout(t);
  }, [q]);

  function go(h: SearchHit | undefined) {
    if (!h) return;
    nav(target(h));
    onClose();
  }

  return (
    <div className="overlay top" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="palette" role="dialog" aria-label="Search">
        <input
          autoFocus
          placeholder="Search projects, tasks, notes, clients, transactions…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Escape') onClose();
            else if (e.key === 'ArrowDown') { e.preventDefault(); setActive((a) => Math.min(a + 1, hits.length - 1)); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
            else if (e.key === 'Enter') go(hits[active]);
          }}
        />
        <ul>
          {hits.map((h, i) => (
            <li key={`${h.kind}-${h.id}`} className={i === active ? 'active' : ''} onMouseEnter={() => setActive(i)} onClick={() => go(h)}>
              <span className="tag">{ICON[h.kind]}</span>
              <span className="grow">{h.title || '(empty)'}</span>
              <small>{h.subtitle}</small>
            </li>
          ))}
          {q.trim().length >= 2 && hits.length === 0 && <li className="none">No results</li>}
        </ul>
      </div>
    </div>
  );
}
