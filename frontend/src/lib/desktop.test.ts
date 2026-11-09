import { afterEach, describe, expect, it, vi } from 'vitest';
import { saveBackup } from './desktop';

const respond = (status: number, body?: unknown) =>
  vi.fn().mockResolvedValue(new Response(body === undefined ? null : JSON.stringify(body), { status }));

afterEach(() => vi.unstubAllGlobals());

describe('saveBackup', () => {
  it('asks the desktop app to show its native save dialog', async () => {
    const f = respond(200, { saved: true });
    const download = vi.fn();
    vi.stubGlobal('fetch', f);
    expect(await saveBackup(true, 'b.json', download)).toBe('saved');
    expect(f.mock.calls[0]![0]).toBe('/api/desktop/backup-file');
    expect(f.mock.calls[0]![1].method).toBe('POST');
    expect(download).not.toHaveBeenCalled();
  });

  it('reports a cancelled dialog', async () => {
    vi.stubGlobal('fetch', respond(200, { saved: false }));
    expect(await saveBackup(true, 'b.json', vi.fn())).toBe('cancelled');
  });

  it('downloads the backup in a normal browser', async () => {
    const f = respond(200, { version: 1 });
    const download = vi.fn();
    vi.stubGlobal('fetch', f);
    expect(await saveBackup(false, 'b.json', download)).toBe('saved');
    expect(f.mock.calls[0]![0]).toBe('/api/backup');
    expect(download).toHaveBeenCalledWith('b.json', JSON.stringify({ version: 1 }, null, 2));
  });

  it('surfaces server errors instead of pretending it saved', async () => {
    vi.stubGlobal('fetch', respond(500, { detail: 'Internal server error' }));
    await expect(saveBackup(true, 'b.json', vi.fn())).rejects.toThrow('Internal server error');
  });
});
