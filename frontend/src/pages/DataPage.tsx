import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { DeleteButton, Dot, Empty, Field } from '../components/ui';
import { ApiError, api } from '../lib/api';
import { CLIENT_COLORS, CURRENCIES, TYPE_LABEL } from '../lib/constants';
import { useData } from '../lib/data';
import { saveBackup } from '../lib/desktop';
import { formatDate, formatMoney, isoToday } from '../lib/format';
import { useToast } from '../lib/toast';
import type { Entry, EntryType, Recurring, Scope } from '../types';

const kindLabel = (scope: Scope, type: EntryType): string =>
  scope === 'personal' ? (type === 'revenue' ? 'Income' : 'Expense') : TYPE_LABEL[type];

export function DataPage() {
  const { profile } = useData();
  return (
    <>
      <header className="page-head"><h1>Settings &amp; data</h1></header>
      <div className="stack">
        <ProfileSection />
        {profile.show_business && <ClientsSection />}
        <MoneySection />
        <BackupSection />
      </div>
    </>
  );
}

function ProfileSection() {
  const { profile, refresh } = useData();
  const toast = useToast();
  const [form, setForm] = useState(profile);
  useEffect(() => setForm(profile), [profile]);
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });
  async function save(e: FormEvent) {
    e.preventDefault();
    try { await api.put('/profile', form); await refresh('profile'); toast.ok('Profile saved'); } catch (err) { toast.fail(err); }
  }
  return (
    <section className="panel">
      <h2 className="section">Profile</h2>
      <form className="form" onSubmit={save}>
        <div className="row">
          <Field label="Name"><input value={form.name} onChange={set('name')} maxLength={200} /></Field>
          <Field label="Company"><input value={form.company} onChange={set('company')} maxLength={200} /></Field>
          <Field label="Contact email"><input type="email" value={form.email} onChange={set('email')} maxLength={320} /></Field>
          <Field label="Currency"><select value={form.currency} onChange={set('currency')}>{CURRENCIES.map((c) => <option key={c}>{c}</option>)}</select></Field>
        </div>
        <label className="toggle">
          <input type="checkbox" checked={form.show_business} onChange={(e) => setForm({ ...form, show_business: e.target.checked })} />
          <span>Show business tools <small className="muted">(projects, clients, business finances). Turn off to keep Cockpit purely personal; nothing is deleted.</small></span>
        </label>
        <footer><span className="spacer" /><button className="primary">Save</button></footer>
      </form>
    </section>
  );
}

function ClientsSection() {
  const { clients, refresh } = useData();
  const toast = useToast();
  const [name, setName] = useState('');
  const [color, setColor] = useState(CLIENT_COLORS[0]!);
  async function add(e: FormEvent) {
    e.preventDefault();
    try { await api.post('/clients', { name, color }); setName(''); await refresh('clients'); } catch (err) { toast.fail(err); }
  }
  async function recolor(id: string, c: string) {
    try { await api.patch(`/clients/${id}`, { color: c }); await refresh('clients'); } catch (err) { toast.fail(err); }
  }
  async function remove(id: string) {
    try { await api.del(`/clients/${id}`); await refresh('clients', 'projects', 'tasks'); } catch (err) { toast.fail(err); }
  }
  return (
    <section className="panel">
      <h2 className="section">Clients</h2>
      <form className="form inline" onSubmit={add}>
        <input className="grow" placeholder="New client name" value={name} onChange={(e) => setName(e.target.value)} maxLength={200} aria-label="Client name" />
        <input type="color" value={color} onChange={(e) => setColor(e.target.value)} aria-label="Colour" />
        <button className="primary" disabled={!name.trim()}>Add</button>
      </form>
      {clients.length === 0 && <Empty>No clients yet. Tasks and projects take their client's colour.</Empty>}
      <ul className="plain">
        {clients.map((c) => (
          <li key={c.id}>
            <Dot color={c.color} /><span className="grow">{c.name}</span>
            <input type="color" value={c.color} onChange={(e) => void recolor(c.id, e.target.value)} aria-label={`Colour for ${c.name}`} />
            <DeleteButton onConfirm={() => void remove(c.id)} />
          </li>
        ))}
      </ul>
    </section>
  );
}

function MoneySection() {
  const { profile } = useData();
  const toast = useToast();
  const [entries, setEntries] = useState<Entry[]>([]);
  const [recurring, setRecurring] = useState<Recurring[]>([]);
  const money = (v: string) => formatMoney(v, profile.currency);
  const load = useCallback(async () => {
    try {
      const [e, r] = await Promise.all([api.get<Entry[]>('/entries'), api.get<Recurring[]>('/recurring')]);
      setEntries(e); setRecurring(r);
    } catch (err) { toast.fail(err); }
  }, [toast]);
  useEffect(() => { void load(); }, [load]);

  const del = (path: string) => async () => { try { await api.del(path); await load(); } catch (e) { toast.fail(e); } };
  /** Flip a transaction between personal and business. */
  async function flipScope(path: string, scope: Scope) {
    try {
      await api.patch(path, { scope: scope === 'personal' ? 'business' : 'personal' });
      await load();
    } catch (e) { toast.fail(e); }
  }
  async function stop(r: Recurring) {
    try { await api.patch(`/recurring/${r.id}`, { end: isoToday() }); await load(); } catch (e) { toast.fail(e); }
  }

  return (
    <>
      <section className="panel">
        <h2 className="section">Transactions</h2>
        <p className="muted">All transactions, personal and business. Add new ones from Money or Business finances.</p>
        {entries.length === 0 && <Empty>No transactions yet.</Empty>}
        <table><tbody>
          {entries.slice(0, 100).map((e) => (
            <tr key={e.id}>
              <td>{e.label} <button className="tag" title="Click to switch personal / business" onClick={() => void flipScope(`/entries/${e.id}`, e.scope)}>{e.scope} ⇄</button><small className="muted block">{formatDate(e.date)} · {kindLabel(e.scope, e.type)} · {e.category}</small></td>
              <td className="num">{money(e.amount)}</td>
              <td className="act"><DeleteButton onConfirm={del(`/entries/${e.id}`)} /></td>
            </tr>
          ))}
        </tbody></table>
      </section>
      <section className="panel">
        <h2 className="section">Recurring items</h2>
        <p className="muted">Subscriptions, retainers and fixed fees. Entered once, counted on each billing day automatically.</p>
        {recurring.length === 0 && <Empty>None yet.</Empty>}
        <table><tbody>
          {recurring.map((r) => {
            const running = !r.end || r.end > isoToday();
            return (
              <tr key={r.id}>
                <td>{r.label} <button className="tag" title="Click to switch personal / business" onClick={() => void flipScope(`/recurring/${r.id}`, r.scope)}>{r.scope} ⇄</button><small className="muted block">{r.frequency} · {kindLabel(r.scope, r.type)} · from {formatDate(r.start)}{r.end ? ` to ${formatDate(r.end)}` : ''}</small></td>
                <td className="num">{money(r.amount)}</td>
                <td className="act">
                  {running && <button onClick={() => void stop(r)}>Stop today</button>}
                  <DeleteButton onConfirm={del(`/recurring/${r.id}`)} />
                </td>
              </tr>
            );
          })}
        </tbody></table>
      </section>
    </>
  );
}

function BackupSection() {
  const { refresh, desktop } = useData();
  const toast = useToast();
  const file = useRef<HTMLInputElement>(null);
  const [pending, setPending] = useState<unknown>(null);

  async function exportJson() {
    try {
      if ((await saveBackup(desktop, `cockpit-backup-${isoToday()}.json`)) === 'saved') toast.ok('Backup saved');
    } catch (e) { toast.fail(e); }
  }
  async function pick(f: File | undefined) {
    if (!f) return;
    try { setPending(JSON.parse(await f.text())); } catch { toast.fail(new ApiError(0, 'That file is not valid JSON')); }
    if (file.current) file.current.value = '';
  }
  async function restore() {
    try {
      await api.post('/backup', pending);
      setPending(null);
      await refresh();
      toast.ok('Backup restored');
    } catch (e) { toast.fail(e); }
  }

  return (
    <section className="panel">
      <h2 className="section">Backup</h2>
      <p className="muted">Everything in Cockpit as one JSON file. Restoring replaces all current data.</p>
      <div className="row">
        <button onClick={() => void exportJson()}>Download backup (.json)</button>
        <input ref={file} type="file" accept="application/json,.json" hidden onChange={(e) => void pick(e.target.files?.[0])} />
        <button onClick={() => file.current?.click()}>Restore from file…</button>
      </div>
      {pending !== null && (
        <div className="notice">
          <p>This will <strong>replace everything</strong> currently stored. Continue?</p>
          <button className="danger" onClick={() => void restore()}>Yes, replace my data</button>
          <button onClick={() => setPending(null)}>Cancel</button>
        </div>
      )}
    </section>
  );
}
