import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { ApiError } from './api';

interface Toast { id: number; text: string; kind: 'error' | 'ok' }
interface ToastApi {
  ok: (text: string) => void;
  /** Reports any error; ApiError messages are already user-readable. */
  fail: (e: unknown) => void;
}

const Ctx = createContext<ToastApi>({ ok: () => undefined, fail: () => undefined });
export const useToast = (): ToastApi => useContext(Ctx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const push = useCallback((text: string, kind: Toast['kind']) => {
    const id = Date.now() + Math.random();
    setItems((cur) => [...cur, { id, text, kind }]);
    setTimeout(() => setItems((cur) => cur.filter((t) => t.id !== id)), kind === 'error' ? 6000 : 2500);
  }, []);
  const api = useMemo<ToastApi>(
    () => ({
      ok: (t) => push(t, 'ok'),
      fail: (e) => push(e instanceof ApiError ? e.message : 'Something went wrong', 'error'),
    }),
    [push],
  );
  return (
    <Ctx.Provider value={api}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={`toast ${t.kind}`}>{t.text}</div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
