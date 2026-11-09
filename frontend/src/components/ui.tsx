import { useEffect, useRef, type ReactNode } from 'react';

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    ref.current?.querySelector<HTMLElement>('input, textarea, select')?.focus();
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);
  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={title} ref={ref}>
        <header>
          <h2>{title}</h2>
          <button className="icon" onClick={onClose} aria-label="Close">×</button>
        </header>
        {children}
      </div>
    </div>
  );
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}

export function Dot({ color }: { color?: string }) {
  return <span className="dot" style={{ background: color ?? 'var(--muted)' }} />;
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="empty">{children}</p>;
}

/** Two-step delete: first click arms the button, second confirms. No window.confirm. */
export function DeleteButton({ onConfirm, label = 'Delete' }: { onConfirm: () => void; label?: string }) {
  const armed = useRef(false);
  const btn = useRef<HTMLButtonElement>(null);
  const timer = useRef<number>(0);
  useEffect(() => () => window.clearTimeout(timer.current), []);
  return (
    <button
      ref={btn}
      className="danger"
      type="button"
      onClick={() => {
        if (armed.current) return onConfirm();
        armed.current = true;
        if (btn.current) btn.current.textContent = 'Click again to confirm';
        timer.current = window.setTimeout(() => {
          armed.current = false;
          if (btn.current) btn.current.textContent = label;
        }, 3000);
      }}
    >
      {label}
    </button>
  );
}

/** Thin progress bar; `marker` (0..1) draws where you "should" be, like the expected pace of a goal. */
export function Progress({ value, marker, tone = 'accent' }: { value: number; marker?: number; tone?: 'accent' | 'ok' | 'late' }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div className="bar" role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100}>
      <i className={tone} style={{ width: `${pct}%` }} />
      {marker !== undefined && <b style={{ left: `${Math.max(0, Math.min(1, marker)) * 100}%` }} title="Expected by now" />}
    </div>
  );
}

export function Pill({ tone, children }: { tone: 'ok' | 'soon' | 'late' | 'muted'; children: ReactNode }) {
  return <span className={`pill ${tone}`}>{children}</span>;
}
