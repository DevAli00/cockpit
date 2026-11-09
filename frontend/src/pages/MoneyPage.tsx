import { useState } from 'react';
import { FundsPanel } from '../components/FundsPanel';
import { NetWorthPanel } from '../components/NetWorthPanel';
import { FinanceView } from './FinancesPage';

export function MoneyPage() {
  const [tab, setTab] = useState<'spending' | 'funds' | 'networth'>('spending');
  return (
    <>
      <header className="page-head">
        <h1>Money</h1>
        <div className="seg" role="tablist">
          <button role="tab" aria-selected={tab === 'spending'} className={tab === 'spending' ? 'on' : ''} onClick={() => setTab('spending')}>Dashboard</button>
          <button role="tab" aria-selected={tab === 'funds'} className={tab === 'funds' ? 'on' : ''} onClick={() => setTab('funds')}>Funds</button>
          <button role="tab" aria-selected={tab === 'networth'} className={tab === 'networth' ? 'on' : ''} onClick={() => setTab('networth')}>Net worth</button>
        </div>
      </header>
      {tab === 'networth' && <NetWorthPanel />}
      {tab === 'funds' && <FundsPanel />}
      {tab === 'spending' && <FinanceView scope="personal" onManageFunds={() => setTab('funds')} />}
    </>
  );
}
