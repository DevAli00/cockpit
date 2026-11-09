import { useCallback, useEffect, useState } from 'react';
import { LibraryPanel } from '../components/LibraryPanel';
import { PathsPanel } from '../components/PathsPanel';
import { api } from '../lib/api';
import { ITEM_KINDS } from '../lib/constants';
import { useToast } from '../lib/toast';
import type { LearningOverview } from '../types';

export function LearningPage() {
  const toast = useToast();
  const [tab, setTab] = useState<'paths' | 'library'>('paths');
  const [stats, setStats] = useState<LearningOverview | null>(null);
  const loadStats = useCallback(() => {
    api.get<LearningOverview>('/learning/overview').then(setStats).catch(toast.fail);
  }, [toast]);
  useEffect(loadStats, [loadStats]);

  return (
    <>
      <header className="page-head">
        <h1>Learning</h1>
        {stats && (
          <div className="chips">
            <span className="chip"><strong>{stats.done_this_year}</strong> finished this year</span>
            <span className="chip"><strong>{stats.in_progress}</strong> in progress</span>
            <span className="chip"><strong>{stats.backlog}</strong> in the backlog</span>
            {Object.entries(stats.done_by_kind).map(([k, n]) => (
              <span key={k} className="chip muted">{n} {ITEM_KINDS.find((x) => x.key === k)?.label.toLowerCase()}{n === 1 ? '' : 's'} done</span>
            ))}
          </div>
        )}
        <div className="seg" role="tablist">
          <button role="tab" aria-selected={tab === 'paths'} className={tab === 'paths' ? 'on' : ''} onClick={() => setTab('paths')}>Paths &amp; milestones</button>
          <button role="tab" aria-selected={tab === 'library'} className={tab === 'library' ? 'on' : ''} onClick={() => setTab('library')}>Library &amp; writing</button>
        </div>
      </header>
      {tab === 'paths' ? <PathsPanel onChanged={loadStats} /> : <LibraryPanel onChanged={loadStats} />}
    </>
  );
}
