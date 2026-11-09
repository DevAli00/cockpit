import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { DeleteButton, Empty, Field, Pill, Progress } from '../components/ui';
import { api } from '../lib/api';
import { TRIP_ITEM_KINDS, TRIP_STATUSES } from '../lib/constants';
import { useData } from '../lib/data';
import { formatDate, formatMoney } from '../lib/format';
import { countdown, num } from '../lib/life';
import { useToast } from '../lib/toast';
import type { Fund, Trip, TripDetail, TripItemKind, TripStatus } from '../types';

export function TripsPage() {
  const { id } = useParams();
  const toast = useToast();
  const nav = useNavigate();
  const { profile } = useData();
  const [trips, setTrips] = useState<Trip[]>([]);
  const [dest, setDest] = useState('');

  const load = useCallback(async () => {
    try { setTrips(await api.get<Trip[]>('/trips')); } catch (e) { toast.fail(e); }
  }, [toast]);
  useEffect(() => { void load(); }, [load]);

  async function add(e: FormEvent) {
    e.preventDefault();
    try {
      const t = await api.post<TripDetail>('/trips', { destination: dest });
      setDest(''); await load(); nav(`/trips/${t.id}`);
    } catch (err) { toast.fail(err); }
  }

  return (
    <div className="split">
      <aside className="panel list">
        <header><h2>Trips</h2></header>
        <form className="form inline" onSubmit={add}>
          <input className="grow" placeholder="Where to?" value={dest} onChange={(e) => setDest(e.target.value)} maxLength={200} aria-label="Destination" />
          <button className="primary small" disabled={!dest.trim()}>Add</button>
        </form>
        {trips.length === 0 && <Empty>No trips yet.</Empty>}
        {trips.map((t) => (
          <Link key={t.id} to={`/trips/${t.id}`} className={`row-link${t.id === id ? ' active' : ''}`}>
            <span className="grow">{t.destination}<small className="muted block">{t.start ? formatDate(t.start) : 'No dates'}{t.days_until !== null && t.status !== 'done' ? ` · ${countdown(t.days_until)}` : ''}</small></span>
            <Pill tone={t.status === 'booked' ? 'ok' : t.status === 'done' ? 'muted' : 'soon'}>{t.status}</Pill>
          </Link>
        ))}
      </aside>
      <div className="detail">
        {id ? <TripView key={id} id={id} currency={profile.currency} onChanged={load} onDeleted={() => { void load(); nav('/trips'); }} /> : <Empty>Select a trip, or add one.</Empty>}
      </div>
    </div>
  );
}

function TripView({ id, currency, onChanged, onDeleted }: { id: string; currency: string; onChanged: () => Promise<void>; onDeleted: () => void }) {
  const toast = useToast();
  const [trip, setTrip] = useState<TripDetail | null>(null);
  const [kind, setKind] = useState<TripItemKind>('todo');
  const [label, setLabel] = useState('');
  const [cost, setCost] = useState('');
  const [when, setWhen] = useState('');

  const [funds, setFunds] = useState<Fund[]>([]);
  const load = useCallback(async () => {
    try {
      const [t, f] = await Promise.all([api.get<TripDetail>(`/trips/${id}`), api.get<Fund[]>(`/funds?trip_id=${id}`)]);
      setTrip(t); setFunds(f);
    } catch (e) { toast.fail(e); }
  }, [id, toast]);
  useEffect(() => { void load(); }, [load]);

  async function patch(body: Record<string, unknown>) {
    try { await api.patch(`/trips/${id}`, body); await load(); await onChanged(); } catch (e) { toast.fail(e); await load(); }
  }
  async function addItem(e: FormEvent) {
    e.preventDefault();
    try {
      await api.post(`/trips/${id}/items`, { kind, label, cost: cost ? cost.replace(',', '.') : null, date: when || null });
      setLabel(''); setCost(''); setWhen('');
      await load(); await onChanged();
    } catch (err) { toast.fail(err); }
  }
  async function patchItem(itemId: string, body: Record<string, unknown>) {
    try { await api.patch(`/trips/items/${itemId}`, body); await load(); await onChanged(); } catch (e) { toast.fail(e); }
  }
  async function delItem(itemId: string) {
    try { await api.del(`/trips/items/${itemId}`); await load(); await onChanged(); } catch (e) { toast.fail(e); }
  }
  async function remove() {
    try { await api.del(`/trips/${id}`); onDeleted(); } catch (e) { toast.fail(e); }
  }

  if (!trip) return <p className="muted">Loading…</p>;
  const money = (v: string | null) => (v === null ? '-' : formatMoney(v, currency));
  const budget = num(trip.budget);
  const over = budget > 0 && num(trip.spent) > budget;

  return (
    <div className="stack">
      <header className="page-head">
        <input className="title-input" defaultValue={trip.destination} maxLength={200} aria-label="Destination"
          onBlur={(e) => { const v = e.target.value.trim(); if (v && v !== trip.destination) void patch({ destination: v }); }} />
        <div className="row">
          <Field label="Status">
            <select value={trip.status} onChange={(e) => void patch({ status: e.target.value as TripStatus })}>
              {TRIP_STATUSES.map((s) => <option key={s}>{s}</option>)}
            </select>
          </Field>
          <Field label="From"><input type="date" defaultValue={trip.start ?? ''} onBlur={(e) => { if (e.target.value !== (trip.start ?? '')) void patch({ start: e.target.value || null }); }} /></Field>
          <Field label="To"><input type="date" defaultValue={trip.end ?? ''} onBlur={(e) => { if (e.target.value !== (trip.end ?? '')) void patch({ end: e.target.value || null }); }} /></Field>
          <Field label="Budget">
            <input inputMode="decimal" defaultValue={trip.budget ?? ''} placeholder="0.00"
              onBlur={(e) => { const v = e.target.value.replace(',', '.'); if (v !== (trip.budget ?? '')) void patch({ budget: v || null }); }} />
          </Field>
        </div>
        {trip.days_until !== null && trip.status !== 'done' && <p className="muted">Departure {countdown(trip.days_until)}.</p>}
      </header>

      <section className="panel">
        <h2 className="section">Budget</h2>
        <p><strong className={over ? 'neg' : ''}>{money(trip.spent)}</strong> planned{budget > 0 && <> of {money(trip.budget)} <span className="muted">({over ? 'over by ' : ''}{money(over ? String(num(trip.spent) - budget) : trip.budget_left)} {over ? '' : 'left'})</span></>}</p>
        {budget > 0 && <Progress value={num(trip.spent) / budget} tone={over ? 'late' : 'accent'} />}
        {funds.map((f) => (
          <p key={f.id} className="muted">Saved for it in “{f.name}”: <strong>{money(f.balance)}</strong> of {money(f.target)}{f.funded ? ' ✓' : ''}</p>
        ))}
        {funds.length === 0 && <p className="hint">Tip: create a travel fund for this trip in Money → Funds.</p>}
      </section>

      <section className="panel">
        <h2 className="section">Plan &amp; checklist <small className="muted">{trip.items_done}/{trip.items_total}</small></h2>
        <form className="form inline" onSubmit={addItem}>
          <select value={kind} onChange={(e) => setKind(e.target.value as TripItemKind)} aria-label="Type">
            {TRIP_ITEM_KINDS.map((k) => <option key={k}>{k}</option>)}
          </select>
          <input className="grow" placeholder="Flight, hotel, visa, activity…" value={label} onChange={(e) => setLabel(e.target.value)} maxLength={300} aria-label="Label" />
          <input type="date" value={when} onChange={(e) => setWhen(e.target.value)} aria-label="Date" />
          <input inputMode="decimal" placeholder="Cost" value={cost} onChange={(e) => setCost(e.target.value)} style={{ width: '6rem' }} aria-label="Cost" />
          <button className="primary" disabled={!label.trim()}>Add</button>
        </form>
        {trip.items.length === 0 && <Empty>Nothing planned yet.</Empty>}
        <ul className="plain">
          {trip.items.map((i) => (
            <li key={i.id} className={i.done ? 'done' : ''}>
              <input type="checkbox" checked={i.done} aria-label={`Mark ${i.label} done`} onChange={(e) => void patchItem(i.id, { done: e.target.checked })} />
              <span className="tag">{i.kind}</span>
              <span className="grow">{i.label}{i.date && <small className="muted"> {formatDate(i.date)}</small>}</span>
              <span className="num">{i.cost !== null ? money(i.cost) : ''}</span>
              <button className="icon" aria-label="Delete item" onClick={() => void delItem(i.id)}>×</button>
            </li>
          ))}
        </ul>
      </section>

      <section className="panel">
        <h2 className="section">Notes</h2>
        <textarea rows={4} defaultValue={trip.notes} maxLength={20000} aria-label="Notes" placeholder="Ideas, contacts, what to bring…"
          onBlur={(e) => { if (e.target.value !== trip.notes) void patch({ notes: e.target.value }); }} />
      </section>
      <footer className="end"><DeleteButton onConfirm={() => void remove()} label="Delete trip" /></footer>
    </div>
  );
}
