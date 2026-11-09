import { Link } from 'react-router-dom';
import { Kanban } from '../components/Kanban';
import { LifeCompass } from '../components/LifeCompass';
import { Dot, Empty } from '../components/ui';
import { useData } from '../lib/data';
import { formatDate } from '../lib/format';
import { greeting } from '../lib/money';

export function OverviewPage() {
  const { projects, clientById, tasks, loading, profile } = useData();
  const active = projects.filter((p) => p.status === 'In progress');
  const open = tasks.filter((t) => t.col !== 'done').length;
  return (
    <>
      <header className="page-head">
        <h1 className="greet">{greeting()}{profile.name ? `, ${profile.name.split(' ')[0]}` : ''}</h1>
        <p className="muted">
          {new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })} · {open} open task{open === 1 ? '' : 's'}
        </p>
      </header>
      <LifeCompass />
      {profile.show_business && <section>
        <h2 className="section">Active projects</h2>
        {active.length === 0 && !loading ? (
          <Empty>No project in progress. <Link to="/projects">Create or start one</Link>.</Empty>
        ) : (
          <div className="chips">
            {active.map((p) => (
              <Link key={p.id} to={`/projects/${p.id}`} className="chip">
                <Dot color={clientById(p.client_id)?.color} />
                <strong>{p.name}</strong>
                {p.deadline && <small>due {formatDate(p.deadline)}</small>}
              </Link>
            ))}
          </div>
        )}
      </section>}
      <section>
        <h2 className="section">Tasks</h2>
        <Kanban />
      </section>
    </>
  );
}
