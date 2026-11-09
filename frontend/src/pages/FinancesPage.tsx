import { useCallback, useEffect, useState } from 'react';
import { FundsStrip } from '../components/FundsStrip';
import { MoneyForm } from '../components/MoneyForms';
import { Empty } from '../components/ui';
import { api } from '../lib/api';
import { PERIODS, TYPE_LABEL } from '../lib/constants';
import { useData } from '../lib/data';
import { formatDate, formatMoney, formatPct, monthLabel } from '../lib/format';
import { moneyLabels } from '../lib/money';
import { useToast } from '../lib/toast';
import type { FinanceSummary, Fund, Period, Scope } from '../types';

/** Business finances page. */
export function FinancesPage() {
  return (
    <>
      <header className="page-head"><h1>Business finances</h1></header>
      <FinanceView scope="business" />
    </>
  );
}

/** Income/expenses for one scope: KPIs, monthly bars, categories, transactions, and quick add. */
export function FinanceView({ scope, onManageFunds }: { scope: Scope; onManageFunds?: () => void }) {
  const { profile, projectById } = useData();
  const toast = useToast();
  const L = moneyLabels(scope);
  const [period, setPeriod] = useState<Period>('month');
  const [data, setData] = useState<FinanceSummary | null>(null);
  const [adding, setAdding] = useState<'one-off' | 'recurring' | null>(null);
  const money = (v: string) => formatMoney(v, profile.currency);
  const [version, setVersion] = useState(0);
  const [funds, setFunds] = useState<Fund[]>([]);
  const fundName = (id: string | null | undefined) => funds.find((f) => f.id === id)?.name;

  const load = useCallback(async () => {
    try {
      const [summary, f] = await Promise.all([
        api.get<FinanceSummary>(`/finance/summary?period=${period}&scope=${scope}`),
        scope === 'personal' ? api.get<Fund[]>('/funds') : Promise.resolve([] as Fund[]),
      ]);
      setData(summary); setFunds(f); setVersion((v) => v + 1);
    } catch (e) { toast.fail(e); }
  }, [period, scope, toast]);
  useEffect(() => { void load(); }, [load]);

  const peak = Math.max(1, ...(data?.by_month.flatMap((m) => [Number(m.revenue), Number(m.costs)]) ?? [0]));
  const t = data?.totals;
  const typeLabel = (type: keyof typeof TYPE_LABEL) => (scope === 'personal' ? (type === 'revenue' ? L.revenue : L.opex) : TYPE_LABEL[type]);

  return (
    <div className="stack">
      <div className="row">
        <div className="seg" role="tablist">
          {PERIODS.map((p) => (
            <button key={p.key} role="tab" aria-selected={p.key === period} className={p.key === period ? 'on' : ''} onClick={() => setPeriod(p.key)}>{p.label}</button>
          ))}
        </div>
        <span className="spacer" />
        <button onClick={() => setAdding(adding === 'one-off' ? null : 'one-off')}>+ Transaction</button>
        <button onClick={() => setAdding(adding === 'recurring' ? null : 'recurring')}>+ Recurring</button>
      </div>

      {adding && (
        <section className="panel">
          <h2 className="section">{adding === 'recurring' ? 'New recurring item (rent, salary, subscriptions…)' : 'New transaction'}</h2>
          <MoneyForm key={adding} scope={scope} recurring={adding === 'recurring'} onSaved={() => { void load(); toast.ok('Saved'); }} />
        </section>
      )}

      {t && (
        <div className="kpis">
          <div className="kpi"><small>{L.revenue}</small><strong>{money(t.revenue)}</strong></div>
          {scope === 'business' && <div className="kpi"><small>{L.direct}</small><strong>{money(t.direct)}</strong></div>}
          <div className="kpi"><small>{L.opex}</small><strong>{money(scope === 'personal' ? String(Number(t.opex) + Number(t.direct)) : t.opex)}</strong></div>
          {scope === 'business' && <div className="kpi"><small>{L.gross}</small><strong>{money(t.gross)}</strong><em>{formatPct(t.gross_rate)}</em></div>}
          {data?.funds && (
            <>
              <div className="kpi"><small>Into funds</small><strong>{money(data.funds.to_funds)}</strong>
                {Number(data.funds.from_funds) > 0 && <em>{money(data.funds.from_funds)} paid from funds</em>}</div>
              <div className={`kpi ${Number(data.funds.left_over) < 0 ? 'neg' : 'pos'}`}><small>Left over to spend</small>
                <strong>{money(data.funds.left_over)}</strong><em>after funds</em></div>
            </>
          )}
          <div className={`kpi ${Number(t.net) < 0 ? 'neg' : 'pos'}`}><small>{L.net}</small><strong>{money(t.net)}</strong><em>{L.netRate} {formatPct(t.net_rate)}</em></div>
        </div>
      )}

      {scope === 'personal' && <FundsStrip version={version} onManage={onManageFunds} />}

      {data && data.by_month.length > 0 && (
        <section className="panel">
          <h2 className="section">By month</h2>
          <div className="bars">
            {data.by_month.map((m) => (
              <div key={m.month} className="bar-col" title={`${monthLabel(m.month)}: ${money(m.revenue)} in, ${money(m.costs)} out`}>
                <div className="pair">
                  <i className="rev" style={{ height: `${(Number(m.revenue) / peak) * 100}%` }} />
                  <i className="cost" style={{ height: `${(Number(m.costs) / peak) * 100}%` }} />
                </div>
                <small>{monthLabel(m.month)}</small>
              </div>
            ))}
          </div>
          <p className="legend"><i className="rev" /> {L.revenue} <i className="cost" /> {L.costs}</p>
        </section>
      )}

      <div className="grid2">
        <section className="panel">
          <h2 className="section">By category</h2>
          {data?.by_category.length === 0 && <Empty>No activity in this period.</Empty>}
          <table><tbody>
            {data?.by_category.map((c) => (
              <tr key={`${c.type}-${c.category}`}><td>{c.category}<small className="muted"> {typeLabel(c.type)}</small></td><td className="num">{money(c.amount)}</td></tr>
            ))}
          </tbody></table>
        </section>
        <section className="panel">
          <h2 className="section">Transactions</h2>
          {data?.transactions.length === 0 && <Empty>Nothing yet. Use “+ Transaction” above.</Empty>}
          <table><tbody>
            {data?.transactions.slice(0, 50).map((x) => (
              <tr key={x.id}>
                <td>{x.label}{x.recurring_id && <small className="muted"> recurring</small>}
                  {fundName(x.fund_id) && <span className="tag">{x.type === 'revenue' ? '→' : '←'} {fundName(x.fund_id)}</span>}
                  <small className="muted block">{formatDate(x.date)} · {x.category}{projectById(x.project_id) ? ` · ${projectById(x.project_id)!.name}` : ''}</small></td>
                <td className={`num ${x.type === 'revenue' ? 'pos' : ''}`}>{x.type === 'revenue' ? '+' : '−'}{money(x.amount)}</td>
              </tr>
            ))}
          </tbody></table>
        </section>
      </div>
    </div>
  );
}
