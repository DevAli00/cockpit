import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { useData } from '../lib/data';
import { formatMoney } from '../lib/format';
import { automationSummary } from '../lib/funds';
import type { Fund } from '../types';
import { Empty, Pill, Progress } from './ui';

/** Compact view of every fund for the money dashboard. Reloads whenever `version` changes. */
export function FundsStrip({ version, onManage }: { version: number; onManage?: () => void }) {
  const { profile } = useData();
  const [funds, setFunds] = useState<Fund[] | null>(null);
  useEffect(() => {
    api.get<Fund[]>('/funds').then(setFunds).catch(() => setFunds([]));
  }, [version]);

  if (funds === null) return null;
  return (
    <section className="panel">
      <header className="card-head">
        <h2 className="section grow">Funds</h2>
        {onManage && <button className="small" onClick={onManage}>Manage funds</button>}
      </header>
      {funds.length === 0 && <Empty>No funds yet. Create a travel or gifts fund in “Funds”, then link expenses to it here.</Empty>}
      <ul className="plain strip">
        {funds.map((f) => {
          const auto = automationSummary(f, profile.currency);
          const overdrawn = Number(f.balance) < 0;
          return (
            <li key={f.id}>
              <span className="strip-name">
                <strong>{f.name}</strong>
                <small className="muted block">{auto || 'filled by hand'}</small>
              </span>
              <span className="grow"><Progress value={f.progress} tone={overdrawn ? 'late' : f.funded ? 'ok' : 'accent'} /></span>
              <span className="num">
                {formatMoney(f.balance, profile.currency)}
                <small className="muted block">of {formatMoney(f.target, profile.currency)}</small>
              </span>
              {overdrawn && <Pill tone="late">Overspent</Pill>}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
