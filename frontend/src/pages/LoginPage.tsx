import { useState, type FormEvent } from 'react';
import { ApiError, api } from '../lib/api';

export function LoginPage({ onLoggedIn }: { onLoggedIn: (email: string) => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const me = await api.post<{ email: string }>('/auth/login', { email, password });
      onLoggedIn(me.email);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Sign-in failed');
      setBusy(false);
    }
  }

  return (
    <main className="login">
      <form onSubmit={submit} className="panel">
        <h1>Cockpit</h1>
        <p className="muted">Sign in to your workspace.</p>
        <label className="field"><span>Email</span>
          <input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
        </label>
        <label className="field"><span>Password</span>
          <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
      </form>
    </main>
  );
}
