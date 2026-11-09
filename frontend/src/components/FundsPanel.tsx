import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { api } from '../lib/api';
import { useData } from '../lib/data';
import { formatDate, formatMoney, isoToday } from '../lib/format';
import { FUND_KINDS, automationSummary, fundKindLabel, missingPresets, ordinal } from '../lib/funds';
import { num } from '../lib/life';
import { useToast } from '../lib/toast';
import type { Fund, FundKind, FundMovement, Trip } from '../types';
import { DeleteButton, Empty, Field, Pill, Progress } from './ui';

export function FundsPanel() {
  const { profile } = useData();
  const toast = useToast();
  const money = (v: string | number) => formatMoney(v, profile.currency);
  const [funds, setFunds] = useState<Fund[]>([]);
  const [trips, setTrips] = useState<Trip[]>([]);
  const [draft, setDraft] = useState<{ name: string; kind: FundKind } | null>(null);

  const load = useCallback(async () => {
    try {
      const [f, t] = await Promise.all([api.get<Fund[]>('/funds'), api.get<Trip[]>('/trips')]);
      setFunds(f); setTrips(t);
    } catch (e) { toast.fail(e); }
  }, [toast]);
  useEffect(() => { void load(); }, [load]);

  const total = funds.reduce((a, f) => a + num(f.balance), 0);
  const monthly = funds.reduce((a, f) => a + num(f.monthly_needed), 0);

  return (
    <div className="stack">
      <section className="panel">
        <div className="nw-head">
          <div>
            <small className="muted">Set aside in funds</small>
            <p className="nw-value">{money(total)}</p>
            <small className="muted">Funds label money that already sits in your accounts; they don't add to net worth.</small>
          </div>
          {monthly > 0 && (
            <div className="nw-split"><span><small className="muted">To stay on schedule</small><strong>{money(monthly)} / month</strong></span></div>
          )}
          <button className="primary" onClick={() => setDraft({ name: '', kind: 'other' })}>+ New fund</button>
        </div>
        {missingPresets(funds).length > 0 && (
          <div className="chips presets">
            <small className="muted">Quick start:</small>
            {missingPresets(funds).map((p) => (
              <button key={p.kind} className="chip" title={p.hint} aria-label={`Create ${p.name} fund`} onClick={() => setDraft({ name: p.name, kind: p.kind })}>+ {p.name}</button>
            ))}
          </div>
        )}
      </section>

      {draft && <NewFund key={`${draft.kind}-${draft.name}`} initial={draft} trips={trips} onClose={() => setDraft(null)} onSaved={async () => { setDraft(null); await load(); }} />}

      {funds.length === 0 && !draft && <Empty>No funds yet. Start with an emergency fund or a travel fund above.</Empty>}
      <div className="grid2">
        {funds.map((f) => (
          <FundCard key={f.id} fund={f} money={money} trip={trips.find((t) => t.id === f.trip_id)} reload={load} />
        ))}
      </div>
    </div>
  );
}

function NewFund({ initial, trips, onClose, onSaved }: {
  initial: { name: string; kind: FundKind }; trips: Trip[]; onClose: () => void; onSaved: () => Promise<void>;
}) {
  const toast = useToast();
  const [f, setF] = useState({ ...initial, target: '', deadline: '', trip_id: '', monthly_amount: '', monthly_day: '1', income_pct: '' });
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });

  async function save(e: FormEvent) {
    e.preventDefault();
    try {
      await api.post('/funds', {
        name: f.name, kind: f.kind, target: f.target.replace(',', '.'),
        deadline: f.deadline || null, trip_id: f.trip_id || null,
        monthly_amount: f.monthly_amount ? f.monthly_amount.replace(',', '.') : null,
        monthly_day: Number(f.monthly_day), income_pct: f.income_pct ? f.income_pct.replace(',', '.') : null,
      });
      await onSaved();
    } catch (err) { toast.fail(err); }
  }

  return (
    <section className="panel">
      <h2 className="section">New fund</h2>
      <form className="form" onSubmit={save}>
        <div className="row">
          <Field label="Name"><input value={f.name} onChange={set('name')} required maxLength={200} autoFocus /></Field>
          <Field label="Kind">
            <select value={f.kind} onChange={set('kind')}>{FUND_KINDS.map((k) => <option key={k.key} value={k.key}>{k.label}</option>)}</select>
          </Field>
          <Field label="Target"><input inputMode="decimal" value={f.target} onChange={set('target')} required placeholder="2400" /></Field>
          <Field label="Deadline (optional)"><input type="date" value={f.deadline} onChange={set('deadline')} /></Field>
          {f.kind === 'travel' && trips.length > 0 && (
            <Field label="For trip (optional)">
              <select value={f.trip_id} onChange={set('trip_id')}>
                <option value="">None</option>
                {trips.map((t) => <option key={t.id} value={t.id}>{t.destination}</option>)}
              </select>
            </Field>
          )}
        </div>
        <AutomationFields monthly={f.monthly_amount} day={f.monthly_day} pct={f.income_pct}
          onChange={(k, v) => setF({ ...f, [k]: v })} />
        <footer><span className="spacer" /><button type="button" onClick={onClose}>Cancel</button><button className="primary" disabled={!f.name.trim() || !f.target}>Create fund</button></footer>
      </form>
    </section>
  );
}

function FundCard({ fund, money, trip, reload }: { fund: Fund; money: (v: string | number) => string; trip?: Trip; reload: () => Promise<void> }) {
  const toast = useToast();
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');
  const [history, setHistory] = useState<FundMovement[] | null>(null);
  const [editingAuto, setEditingAuto] = useState(false);
  const { profile } = useData();
  const auto = automationSummary(fund, profile.currency);

  const loadHistory = useCallback(async () => {
    try { setHistory(await api.get<FundMovement[]>(`/funds/${fund.id}/ledger`)); } catch (e) { toast.fail(e); }
  }, [fund.id, toast]);

  async function move(sign: 1 | -1) {
    const v = amount.replace(',', '.').trim();
    if (!v || Number(v) <= 0) return;
    try {
      await api.post(`/funds/${fund.id}/contributions`, { date: isoToday(), amount: sign < 0 ? `-${v}` : v, note });
      setAmount(''); setNote('');
      await reload();
      if (history) await loadHistory();
    } catch (e) { toast.fail(e); }
  }
  async function undo(m: FundMovement) {
    if (m.source !== 'manual' || !m.ref) return;
    try { await api.del(`/funds/contributions/${m.ref}`); await reload(); await loadHistory(); } catch (e) { toast.fail(e); }
  }
  async function remove() {
    try { await api.del(`/funds/${fund.id}`); await reload(); } catch (e) { toast.fail(e); }
  }

  return (
    <article className="panel">
      <header className="card-head">
        <div className="grow">
          <h3>{fund.name}</h3>
          <small className="muted">
            {fundKindLabel(fund.kind)}{fund.deadline && ` · by ${formatDate(fund.deadline)}`}{trip && ` · for ${trip.destination}`}
          </small>
        </div>
        {fund.funded ? <Pill tone="ok">Funded</Pill> : null}
      </header>
      <p><strong className="big">{money(fund.balance)}</strong> <span className="muted">of {money(fund.target)}</span></p>
      <Progress value={fund.progress} tone={fund.funded ? 'ok' : 'accent'} />
      {!fund.funded && (
        <small className="muted">
          {money(fund.remaining)} to go
          {fund.monthly_needed !== null && ` · ${money(fund.monthly_needed)}/month or ${money(fund.weekly_needed ?? 0)}/week`}
        </small>
      )}
      <p className="auto-line">
        <small className="muted">{auto ? `Automatic: ${auto}` : 'Filled by hand'}</small>
        <button className="small" onClick={() => setEditingAuto((v) => !v)}>{editingAuto ? 'Close' : auto ? 'Edit automation' : 'Automate'}</button>
      </p>
      {editingAuto && <AutomationEditor fund={fund} onSaved={async () => { setEditingAuto(false); await reload(); if (history) await loadHistory(); }} />}
      <div className="form inline fund-move">
        <input inputMode="decimal" placeholder="Amount" value={amount} onChange={(e) => setAmount(e.target.value)} aria-label="Amount" style={{ width: '7rem' }} />
        <input className="grow" placeholder="Note (optional)" value={note} onChange={(e) => setNote(e.target.value)} maxLength={300} aria-label="Note" />
        <button className="primary" onClick={() => void move(1)} disabled={!amount.trim()}>Add</button>
        <button onClick={() => void move(-1)} disabled={!amount.trim()}>Take out</button>
      </div>
      <footer className="row">
        <button className="small" onClick={() => (history ? setHistory(null) : void loadHistory())}>
          {history ? 'Hide history' : `History (${fund.contributions})`}
        </button>
        <span className="spacer" />
        <DeleteButton onConfirm={() => void remove()} label="Delete fund" />
      </footer>
      {history && (
        <table><tbody>
          {history.length === 0 && <tr><td className="muted">Nothing yet.</td></tr>}
          {history.map((m, i) => (
            <tr key={`${m.source}-${m.ref ?? ''}-${m.date}-${i}`}>
              <td>{formatDate(m.date)} <span className="tag">{SOURCE_LABEL[m.source]}</span><small className="muted block">{m.label}</small></td>
              <td className={`num ${num(m.amount) < 0 ? 'neg' : 'pos'}`}>{num(m.amount) < 0 ? '−' : '+'}{money(Math.abs(num(m.amount)))}</td>
              <td className="act">{m.source === 'manual' && <button className="icon" aria-label="Remove this movement" onClick={() => void undo(m)}>×</button>}</td>
            </tr>
          ))}
        </tbody></table>
      )}
    </article>
  );
}


const SOURCE_LABEL: Record<FundMovement['source'], string> = {
  manual: 'by hand', monthly: 'monthly', income_share: 'from income', expense: 'expense', income: 'income',
};

function AutomationFields({ monthly, day, pct, onChange }: {
  monthly: string; day: string; pct: string; onChange: (k: 'monthly_amount' | 'monthly_day' | 'income_pct', v: string) => void;
}) {
  return (
    <div className="row auto-fields">
      <Field label="Put in every month (optional)">
        <input inputMode="decimal" value={monthly} onChange={(e) => onChange('monthly_amount', e.target.value)} placeholder="e.g. 200" />
      </Field>
      <Field label="On day">
        <select value={day} onChange={(e) => onChange('monthly_day', e.target.value)}>
          {Array.from({ length: 28 }, (_, i) => i + 1).map((d) => <option key={d} value={d}>{ordinal(d)}</option>)}
        </select>
      </Field>
      <Field label="% of every income (optional)">
        <input inputMode="decimal" value={pct} onChange={(e) => onChange('income_pct', e.target.value)} placeholder="e.g. 10" />
      </Field>
    </div>
  );
}

function AutomationEditor({ fund, onSaved }: { fund: Fund; onSaved: () => Promise<void> }) {
  const toast = useToast();
  const [v, setV] = useState({
    monthly_amount: fund.monthly_amount === null ? '' : String(Number(fund.monthly_amount)),
    monthly_day: String(fund.monthly_day),
    income_pct: fund.income_pct === null ? '' : String(Number(fund.income_pct)),
  });
  async function save(e: FormEvent) {
    e.preventDefault();
    try {
      await api.patch(`/funds/${fund.id}`, {
        monthly_amount: v.monthly_amount ? v.monthly_amount.replace(',', '.') : null,
        monthly_day: Number(v.monthly_day),
        income_pct: v.income_pct ? v.income_pct.replace(',', '.') : null,
      });
      toast.ok('Automation saved');
      await onSaved();
    } catch (err) { toast.fail(err); }
  }
  return (
    <form className="form" onSubmit={save}>
      <AutomationFields monthly={v.monthly_amount} day={v.monthly_day} pct={v.income_pct} onChange={(k, val) => setV({ ...v, [k]: val })} />
      <p className="hint">Changes apply from today. What the old rule already put in stays as it was.</p>
      <footer><span className="spacer" /><button className="primary">Save automation</button></footer>
    </form>
  );
}
