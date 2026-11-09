import { useEffect, useState, type FormEvent } from 'react';
import { api } from '../lib/api';
import { CATEGORIES, PERSONAL_CATEGORIES, TYPE_LABEL } from '../lib/constants';
import { useData } from '../lib/data';
import { isoToday } from '../lib/format';
import { useToast } from '../lib/toast';
import type { EntryType, Frequency, Fund, Scope } from '../types';
import { Field } from './ui';

const BUSINESS_TYPES = Object.keys(TYPE_LABEL) as EntryType[];
const PERSONAL_TYPES: EntryType[] = ['opex', 'revenue'];
const PERSONAL_LABEL: Partial<Record<EntryType, string>> = { revenue: 'Income', opex: 'Expense' };

const categoriesFor = (scope: Scope, t: EntryType): string[] =>
  scope === 'personal' ? PERSONAL_CATEGORIES[t === 'revenue' ? 'revenue' : 'opex'] : CATEGORIES[t];

interface Props { recurring?: boolean; scope?: Scope; onSaved: () => void }

/** One form for both one-off transactions and recurring items. */
export function MoneyForm({ recurring = false, scope = 'business', onSaved }: Props) {
  const types = scope === 'personal' ? PERSONAL_TYPES : BUSINESS_TYPES;
  const { projects } = useData();
  const toast = useToast();
  const [type, setType] = useState<EntryType>(types[0]!);
  const [category, setCategory] = useState(categoriesFor(scope, types[0]!)[0]!);
  const [label, setLabel] = useState('');
  const [amount, setAmount] = useState('');
  const [date, setDate] = useState(isoToday());
  const [frequency, setFrequency] = useState<Frequency>('monthly');
  const [projectId, setProjectId] = useState('');
  const [fundId, setFundId] = useState('');
  const [funds, setFunds] = useState<Fund[]>([]);
  useEffect(() => {
    if (scope !== 'personal') return;
    api.get<Fund[]>('/funds').then(setFunds).catch(() => setFunds([]));
  }, [scope]);

  function changeType(t: EntryType) {
    setType(t);
    setCategory(categoriesFor(scope, t)[0]!);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    const common = {
      scope, label, type, category, amount: amount.replace(',', '.'), project_id: projectId || null,
      fund_id: scope === 'personal' ? fundId || null : null,
    };
    try {
      if (recurring) await api.post('/recurring', { ...common, frequency, start: date });
      else await api.post('/entries', { ...common, date });
      setLabel('');
      setAmount('');
      onSaved();
    } catch (err) { toast.fail(err); }
  }

  return (
    <form className="form" onSubmit={submit}>
      <div className="row">
        <Field label="Type">
          <select value={type} onChange={(e) => changeType(e.target.value as EntryType)}>
            {types.map((t) => <option key={t} value={t}>{scope === 'personal' ? PERSONAL_LABEL[t] : TYPE_LABEL[t]}</option>)}
          </select>
        </Field>
        <Field label="Category">
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            {categoriesFor(scope, type).map((c) => <option key={c}>{c}</option>)}
          </select>
        </Field>
        {scope === 'business' && (
          <Field label="Project">
            <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              <option value="">None</option>
              {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </Field>
        )}
        {scope === 'personal' && funds.length > 0 && (
          <Field label={type === 'revenue' ? 'Goes into fund (optional)' : 'Paid from fund (optional)'}>
            <select value={fundId} onChange={(e) => setFundId(e.target.value)}>
              <option value="">{type === 'revenue' ? 'No, normal income' : 'No, my everyday money'}</option>
              {funds.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
            </select>
          </Field>
        )}
      </div>
      <div className="row">
        <Field label="Label"><input value={label} onChange={(e) => setLabel(e.target.value)} required maxLength={300} /></Field>
        <Field label="Amount"><input inputMode="decimal" pattern="[0-9]+([.,][0-9]{1,2})?" value={amount} onChange={(e) => setAmount(e.target.value)} required placeholder="0.00" /></Field>
        {recurring && (
          <Field label="Every">
            <select value={frequency} onChange={(e) => setFrequency(e.target.value as Frequency)}>
              <option value="monthly">Month</option><option value="yearly">Year</option>
            </select>
          </Field>
        )}
        <Field label={recurring ? 'Starts' : 'Date'}><input type="date" value={date} onChange={(e) => setDate(e.target.value)} required /></Field>
      </div>
      <footer><span className="spacer" /><button className="primary">{recurring ? 'Add recurring item' : 'Add transaction'}</button></footer>
    </form>
  );
}
