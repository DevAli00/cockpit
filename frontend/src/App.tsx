import { useEffect, useState } from 'react';
import { BrowserRouter, NavLink, Navigate, Route, Routes } from 'react-router-dom';
import { SearchPalette } from './components/SearchPalette';
import { api, onUnauthorized } from './lib/api';
import { DataProvider, useData } from './lib/data';
import { ToastProvider } from './lib/toast';
import { DataPage } from './pages/DataPage';
import { FinancesPage } from './pages/FinancesPage';
import { GoalsPage } from './pages/GoalsPage';
import { LearningPage } from './pages/LearningPage';
import { TripsPage } from './pages/TripsPage';
import { WeeklyPage } from './pages/WeeklyPage';
import { LoginPage } from './pages/LoginPage';
import { MoneyPage } from './pages/MoneyPage';
import { OverviewPage } from './pages/OverviewPage';
import { ProjectsPage } from './pages/ProjectsPage';

type Session = { state: 'loading' } | { state: 'anon' } | { state: 'in'; email: string; desktop: boolean };

export default function App() {
  const [session, setSession] = useState<Session>({ state: 'loading' });

  useEffect(() => {
    onUnauthorized(() => setSession({ state: 'anon' }));
    api.get<{ email: string; desktop?: boolean }>('/me')
      .then((me) => setSession({ state: 'in', email: me.email, desktop: me.desktop === true }))
      .catch(() => setSession({ state: 'anon' }));
    return () => onUnauthorized(null);
  }, []);

  if (session.state === 'loading') return <div className="boot">Loading…</div>;
  return (
    <ToastProvider>
      {session.state === 'anon' ? (
        <LoginPage onLoggedIn={(email) => setSession({ state: 'in', email, desktop: false })} />
      ) : (
        <DataProvider desktop={session.desktop}>
          <BrowserRouter>
            <Shell email={session.email} desktop={session.desktop} onLogout={() => setSession({ state: 'anon' })} />
          </BrowserRouter>
        </DataProvider>
      )}
    </ToastProvider>
  );
}

function Shell({ email, desktop, onLogout }: { email: string; desktop: boolean; onLogout: () => void }) {
  const { profile, loading } = useData();
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setSearching(true); }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  async function logout() {
    await api.post('/auth/logout').catch(() => undefined);
    onLogout();
  }

  return (
    <div className="shell">
      <nav className="side">
        <div className="brand">Cockpit</div>
        <button className="search-btn" onClick={() => setSearching(true)}>Search <kbd>⌘K</kbd></button>
        <NavLink to="/" end>Today</NavLink>
        <small className="nav-group">Life</small>
        <NavLink to="/goals">North Star</NavLink>
        <NavLink to="/weekly">Weekly check</NavLink>
        <NavLink to="/learning">Learning</NavLink>
        <NavLink to="/trips">Trips</NavLink>
        <NavLink to="/money">Money</NavLink>
        {profile.show_business && (
          <>
            <small className="nav-group">Business</small>
            <NavLink to="/projects">Projects</NavLink>
            <NavLink to="/finances">Finances</NavLink>
          </>
        )}
        <hr />
        <NavLink to="/data">Settings &amp; data</NavLink>
        <span className="spacer" />
        <div className="who"><strong>{profile.name || (desktop ? 'My cockpit' : email)}</strong><small>{profile.show_business ? profile.company : ''}</small></div>
        {!desktop && <button onClick={() => void logout()}>Sign out</button>}
      </nav>
      <main className="content">
        {loading ? <p className="muted">Loading…</p> : (
          <Routes>
            <Route path="/" element={<OverviewPage />} />
            <Route path="/projects/:id?" element={<ProjectsPage />} />
            <Route path="/finances" element={<FinancesPage />} />
            <Route path="/goals" element={<GoalsPage />} />
            <Route path="/weekly" element={<WeeklyPage />} />
            <Route path="/learning" element={<LearningPage />} />
            <Route path="/trips/:id?" element={<TripsPage />} />
            <Route path="/money" element={<MoneyPage />} />
            <Route path="/data" element={<DataPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        )}
      </main>
      {searching && <SearchPalette onClose={() => setSearching(false)} />}
    </div>
  );
}
