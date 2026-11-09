export class ApiError extends Error {
  constructor(readonly status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

let unauthorizedHandler: (() => void) | null = null;
/** Register what happens when the session expires (any 401): the app shows the login page. */
export const onUnauthorized = (cb: (() => void) | null): void => {
  unauthorizedHandler = cb;
};

interface ValidationItem { loc?: unknown[]; msg?: string }

function detailToMessage(detail: unknown, status: number): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return (detail as ValidationItem[])
      .map((d) => `${(d.loc ?? []).filter((p) => p !== 'body').join('.')}: ${d.msg ?? 'invalid'}`)
      .join('; ');
  }
  return `Request failed (${status})`;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      method,
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "Can't reach the server. Check that Cockpit is running.");
  }
  if (res.status === 204) return undefined as T;
  const data: unknown = await res.json().catch(() => undefined);
  if (!res.ok) {
    if (res.status === 401) unauthorizedHandler?.();
    const detail = (data as { detail?: unknown } | undefined)?.detail;
    throw new ApiError(res.status, detailToMessage(detail, res.status));
  }
  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  patch: <T>(path: string, body: unknown) => request<T>('PATCH', path, body),
  put: <T>(path: string, body: unknown) => request<T>('PUT', path, body),
  del: (path: string) => request<void>('DELETE', path),
};
