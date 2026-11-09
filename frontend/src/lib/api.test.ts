import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, api, onUnauthorized } from './api';

const respond = (status: number, body?: unknown) =>
  vi.fn().mockResolvedValue(new Response(body === undefined ? null : JSON.stringify(body), { status }));

afterEach(() => vi.unstubAllGlobals());

describe('api', () => {
  it('sends JSON with credentials and parses the response', async () => {
    const f = respond(200, { ok: 1 });
    vi.stubGlobal('fetch', f);
    expect(await api.post('/x', { a: 1 })).toEqual({ ok: 1 });
    const [url, init] = f.mock.calls[0]!;
    expect(url).toBe('/api/x');
    expect(init.method).toBe('POST');
    expect(init.credentials).toBe('same-origin');
    expect(init.headers['Content-Type']).toBe('application/json');
  });

  it('returns undefined for 204', async () => {
    vi.stubGlobal('fetch', respond(204));
    expect(await api.del('/x')).toBeUndefined();
  });

  it('throws ApiError with the server detail', async () => {
    vi.stubGlobal('fetch', respond(422, { detail: 'nope' }));
    await expect(api.get('/x')).rejects.toMatchObject({ status: 422, message: 'nope' });
  });

  it('flattens FastAPI validation errors', async () => {
    vi.stubGlobal('fetch', respond(422, { detail: [{ loc: ['body', 'name'], msg: 'too short' }] }));
    await expect(api.post('/x', {})).rejects.toThrow('name: too short');
  });

  it('survives a non-JSON error body', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>', { status: 502 })));
    const err = await api.get('/x').catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(502);
  });

  it('notifies on 401 so the app can show the login page', async () => {
    const cb = vi.fn();
    onUnauthorized(cb);
    vi.stubGlobal('fetch', respond(401, { detail: 'Not authenticated' }));
    await expect(api.get('/me')).rejects.toBeInstanceOf(ApiError);
    expect(cb).toHaveBeenCalled();
  });

  it('wraps network failures in a readable error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    await expect(api.get('/x')).rejects.toThrow(/reach the server/i);
  });
});
