import { api } from './api';

function browserDownload(name: string, content: string): void {
  const url = URL.createObjectURL(new Blob([content], { type: 'application/json' }));
  const a = Object.assign(document.createElement('a'), { href: url, download: name });
  a.click();
  URL.revokeObjectURL(url);
}

/**
 * Save the full backup to a file. In the desktop app the local server opens a native save dialog
 * (embedded web views do not reliably support downloads); in a browser it is a normal download.
 */
export async function saveBackup(
  desktop: boolean, name: string, download: (name: string, content: string) => void = browserDownload,
): Promise<'saved' | 'cancelled'> {
  if (desktop) {
    const { saved } = await api.post<{ saved: boolean }>('/desktop/backup-file');
    return saved ? 'saved' : 'cancelled';
  }
  download(name, JSON.stringify(await api.get<unknown>('/backup'), null, 2));
  return 'saved';
}
