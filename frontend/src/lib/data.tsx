import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import type { Client, Profile, Project, Task } from '../types';
import { api } from './api';
import { useToast } from './toast';

type Slice = 'profile' | 'clients' | 'projects' | 'tasks';

interface DataState {
  profile: Profile;
  clients: Client[];
  projects: Project[];
  tasks: Task[];
  loading: boolean;
  /** True inside the standalone desktop app. */
  desktop: boolean;
  refresh: (...slices: Slice[]) => Promise<void>;
  /** Replace tasks locally (optimistic drag and drop); refresh() reconciles with the server. */
  setTasks: (updater: (cur: Task[]) => Task[]) => void;
  clientById: (id: string | null) => Client | undefined;
  projectById: (id: string | null) => Project | undefined;
}

const EMPTY_PROFILE: Profile = { name: '', email: '', company: '', currency: 'EUR', show_business: true };
const PATHS: Record<Slice, string> = {
  profile: '/profile', clients: '/clients', projects: '/projects', tasks: '/tasks',
};

const Ctx = createContext<DataState | null>(null);

export function useData(): DataState {
  const v = useContext(Ctx);
  if (!v) throw new Error('useData outside DataProvider');
  return v;
}

export function DataProvider({ children, desktop = false }: { children: ReactNode; desktop?: boolean }) {
  const toast = useToast();
  const [profile, setProfile] = useState<Profile>(EMPTY_PROFILE);
  const [clients, setClients] = useState<Client[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [tasks, setTasksState] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(
    async (...slices: Slice[]) => {
      const which: Slice[] = slices.length ? slices : ['profile', 'clients', 'projects', 'tasks'];
      try {
        const results = await Promise.all(which.map((s) => api.get<unknown>(PATHS[s])));
        which.forEach((s, i) => {
          const r = results[i];
          if (s === 'profile') setProfile(r as Profile);
          else if (s === 'clients') setClients(r as Client[]);
          else if (s === 'projects') setProjects(r as Project[]);
          else setTasksState(r as Task[]);
        });
      } catch (e) {
        toast.fail(e);
      }
    },
    [toast],
  );

  useEffect(() => {
    void refresh().finally(() => setLoading(false));
  }, [refresh]);

  const value = useMemo<DataState>(
    () => ({
      profile, clients, projects, tasks, loading, refresh, desktop,
      setTasks: (updater) => setTasksState(updater),
      clientById: (id) => (id ? clients.find((c) => c.id === id) : undefined),
      projectById: (id) => (id ? projects.find((p) => p.id === id) : undefined),
    }),
    [profile, clients, projects, tasks, loading, refresh, desktop],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
