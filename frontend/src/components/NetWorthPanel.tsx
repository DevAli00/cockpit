import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { api } from '../lib/api';
import { useData } from '../lib/data';
import { formatDate, formatMoney, isoToday } from '../lib/format';
import { ACCOUNT_TYPES, accountKind, accountLabel, chartPoints, signedMoney } from '../lib/money';
import { useToast } from '../lib/toast';
import type { Account, AccountType, NetWorthSummary } from '../types';
import { DeleteButton, Empty, Field, Pill } from './ui';

const CHART_W = 600;
const CHART_H = 140;

export function NetWorthPanel() {
  const { profile } = useData();
  const toast = useToast();
  const money = (v: string | number) => formatMoney(v, profile.currency);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [summary, setSummary] = useState<NetWorthSummary | null>(null);
  const [updating, setUpdating] = useState(false);

  const load = useCallback(async () => {
    try {
      const [a, s] = await Promise.all([api.get<Account[]>('/networth/accounts'), api.get<NetWorthSummary>('/networth/summary')]);
      setAccounts(a); setSummary(s);
    } catch (e) { toast.fail(e); }
  }, [toast]);
  useEffect(() => { void load(); }, [load]);

  const series = useMemo(() => summary?.history.map((p) => Number(p.net)) ?? [], [summary]);
  const peakType = Math.max(1, ...(summary?.by_type.map((t) => Math.abs(Number(t.amount))) ?? [1]));

  async function remove(a: Account) {
    try { await api.del(`/networth/accounts/${a.id}`); await load(); } catch (e) { toast.fail(e); }
  }

  return (
    <div className="stack">
      {summary && (
        <section className="panel networth">
          <div className="nw-head">
            <div>
              <small className="muted">Net worth</small>
              <p className={`nw-value${Number(summary.net) < 0 ? ' neg' : ''}`}>{money(summary.net)}</p>
              {summary.change_30d !== null && (
                <small className={Number(summary.change_30d) >= 0 ? 'pos' : 'neg'}>{signedMoney(summary.change_30d, profile.currency)} over 30 days</small>
              )}
            </div>
            <div className="nw-split">
              <span><small className="muted">Assets</small><strong>{money(summary.assets)}</strong></span>
              <span><small className="muted">Debts</small><strong>{money(summary.liabilities)}</strong></span>
            </div>
            <button className="primary" onClick={() => setUpdating((u) => !u)} disabled={!accounts.length}>Update balances</button>
          </div>
          {summary.stale_accounts > 0 && (
            <p className="hint"><Pill tone="soon">{summary.stale_accounts} account{summary.stale_accounts === 1 ? '' : 's'} not updated in 45 days</Pill></p>
          )}
          {series.length > 1 && (
            <svg className="nw-chart" viewBox={`0 0 ${CHART_W} ${CHART_H}`} preserveAspectRatio="none" role="img"
              aria-label={`Net worth from ${money(series[0]!)} to ${money(series[series.length - 1]!)}`}>
              <polyline points={chartPoints(series, CHART_W, CHART_H)} fill="none" stroke="var(--accent)" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />
            </svg>
          )}
          {summary.history.length > 1 && (
            <div className="nw-axis"><small>{formatDate(summary.history[0]!.at)}</small><small>{formatDate(summary.history[summary.history.length - 1]!.at)}</small></div>
          )}
        </section>
      )}

      {updating && <UpdateBalances accounts={accounts} onDone={() => { setUpdating(false); void load(); }} />}

      <div className="grid2">
        <section className="panel">
          <h2 className="section">Accounts</h2>
          {accounts.length === 0 && <Empty>Add what you own and what you owe: bank accounts, savings, investments, crypto, car, loans…</Empty>}
          {(['asset', 'liability'] as const).map((kind) => {
            const list = accounts.filter((a) => a.kind === kind);
            if (!list.length) return null;
            return (
              <div key={kind}>
                <h3 className="sub">{kind === 'asset' ? 'Assets' : 'Debts'}</h3>
                <table><tbody>
                  {list.map((a) => (
                    <tr key={a.id}>
                      <td>{a.name}<small className="muted block">{accountLabel(a.type)}{a.institution && ` · ${a.institution}`}{a.as_of && ` · ${formatDate(a.as_of)}`}</small></td>
                      <td className={`num${kind === 'liability' ? ' neg' : ''}`}>{a.balance === null ? <small className="muted">no balance</small> : money(a.balance)}</td>
                      <td className="act"><DeleteButton onConfirm={() => void remove(a)} /></td>
                    </tr>
                  ))}
                </tbody></table>
              </div>
            );
          })}
          <NewAccount onSaved={load} />
        </section>

        <section className="panel">
          <h2 className="section">Where it sits</h2>
          {!summary?.by_type.length && <Empty>Add balances to see your allocation.</Empty>}
          <ul className="plain alloc">
            {summary?.by_type.map((t) => (
              <li key={t.type}>
                <span className="grow">{accountLabel(t.type)}</span>
                <span className="alloc-bar"><i className={t.kind === 'liability' ? 'debt' : ''} style={{ width: `${(Math.abs(Number(t.amount)) / peakType) * 100}%` }} /></span>
                <span className={`num${t.kind === 'liability' ? ' neg' : ''}`}>{t.kind === 'liability' ? '−' : ''}{money(t.amount)}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}

function NewAccount({ onSaved }: { onSaved: () => Promise<void> }) {
  const toast = useToast();
  const [name, setName] = useState('');
  const [type, setType] = useState<AccountType>('cash');
  const [institution, setInstitution] = useState('');
  const [balance, setBalance] = useState('');

  async function add(e: FormEvent) {
    e.preventDefault();
    try {
      const a = await api.post<Account>('/networth/accounts', { name, type, institution });
      if (balance.trim()) await api.post(`/networth/accounts/${a.id}/balances`, { date: isoToday(), balance: balance.replace(',', '.') });
      setName(''); setInstitution(''); setBalance('');
      await onSaved();
    } catch (err) { toast.fail(err); }
  }

  return (
    <form className="form" onSubmit={add}>
      <h3 className="sub">Add an account</h3>
      <div className="row">
        <Field label="Name"><input value={name} onChange={(e) => setName(e.target.value)} placeholder="Livret A, PEA, Car loan…" maxLength={200} required /></Field>
        <Field label="Type">
          <select value={type} onChange={(e) => setType(e.target.value as AccountType)}>
            <optgroup label="Assets">{ACCOUNT_TYPES.filter((t) => t.kind === 'asset').map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}</optgroup>
            <optgroup label="Debts">{ACCOUNT_TYPES.filter((t) => t.kind === 'liability').map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}</optgroup>
          </select>
        </Field>
      </div>
      <div className="row">
        <Field label="Bank / where"><input value={institution} onChange={(e) => setInstitution(e.target.value)} maxLength={200} /></Field>
        <Field label={accountKind(type) === 'liability' ? 'Amount owed today' : 'Balance today'}>
          <input inputMode="decimal" value={balance} onChange={(e) => setBalance(e.target.value)} placeholder="0.00" />
        </Field>
      </div>
      <footer><span className="spacer" /><button className="primary" disabled={!name.trim()}>Add account</button></footer>
    </form>
  );
}

/** The monthly ritual: one date, every balance, one save. Pre-filled with the last known values. */
function UpdateBalances({ accounts, onDone }: { accounts: Account[]; onDone: () => void }) {
  const toast = useToast();
  const [date, setDate] = useState(isoToday());
  const [values, setValues] = useState<Record<string, string>>(
    Object.fromEntries(accounts.map((a) => [a.id, a.balance === null ? '' : String(Number(a.balance))])),
  );

  async function save(e: FormEvent) {
    e.preventDefault();
    const balances = Object.fromEntries(
      Object.entries(values).filter(([, v]) => v.trim() !== '').map(([k, v]) => [k, v.replace(',', '.')]),
    );
    try {
      await api.post('/networth/update', { date, balances });
      toast.ok('Balances saved');
      onDone();
    } catch (err) { toast.fail(err); }
  }

  return (
    <section className="panel">
      <h2 className="section">Update balances</h2>
      <form className="form" onSubmit={save}>
        <Field label="As of"><input type="date" value={date} max={isoToday()} onChange={(e) => setDate(e.target.value)} required /></Field>
        <div className="row">
          {accounts.map((a) => (
            <Field key={a.id} label={`${a.name}${a.kind === 'liability' ? ' (owed)' : ''}`}>
              <input inputMode="decimal" value={values[a.id] ?? ''} onChange={(e) => setValues({ ...values, [a.id]: e.target.value })} placeholder="-" />
            </Field>
          ))}
        </div>
        <footer><span className="spacer" /><button type="button" onClick={onDone}>Cancel</button><button className="primary">Save balances</button></footer>
      </form>
    </section>
  );
}
