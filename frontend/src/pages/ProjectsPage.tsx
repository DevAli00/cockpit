import { useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { DeleteButton, Dot, Empty, Field, Modal } from '../components/ui';
import { api } from '../lib/api';
import { NOTE_KINDS, PROJECT_STATUSES } from '../lib/constants';
import { useData } from '../lib/data';
import { formatDate, isoToday } from '../lib/format';
import { useToast } from '../lib/toast';
import type { Brief, Note, NoteKind, Project, ProjectStatus } from '../types';

export function ProjectsPage() {
  const { id } = useParams();
  const { projects, clientById } = useData();
  const [creating, setCreating] = useState(false);
  const selected = projects.find((p) => p.id === id);
  return (
    <div className="split">
      <aside className="panel list">
        <header>
          <h2>Projects</h2>
          <button className="primary small" onClick={() => setCreating(true)}>+ New</button>
        </header>
        {projects.length === 0 && <Empty>No projects yet.</Empty>}
        {projects.map((p) => (
          <Link key={p.id} to={`/projects/${p.id}`} className={`row-link${p.id === id ? ' active' : ''}`}>
            <Dot color={clientById(p.client_id)?.color} />
            <span className="grow">{p.name}</span>
            <small className="muted">{p.status}</small>
          </Link>
        ))}
      </aside>
      <div className="detail">
        {selected ? <ProjectDetail key={selected.id} project={selected} /> : <Empty>Select a project, or create one.</Empty>}
      </div>
      {creating && <NewProject onClose={() => setCreating(false)} />}
    </div>
  );
}

function NewProject({ onClose }: { onClose: () => void }) {
  const { clients, refresh } = useData();
  const toast = useToast();
  const nav = useNavigate();
  const [name, setName] = useState('');
  const [clientId, setClientId] = useState('');
  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      const p = await api.post<Project>('/projects', { name, client_id: clientId || null });
      await refresh('projects');
      onClose();
      nav(`/projects/${p.id}`);
    } catch (err) { toast.fail(err); }
  }
  return (
    <Modal title="New project" onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <Field label="Name"><input value={name} onChange={(e) => setName(e.target.value)} required maxLength={200} /></Field>
        <Field label="Client">
          <select value={clientId} onChange={(e) => setClientId(e.target.value)}>
            <option value="">None</option>
            {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </Field>
        <footer><span className="spacer" /><button type="button" onClick={onClose}>Cancel</button><button className="primary" disabled={!name.trim()}>Create</button></footer>
      </form>
    </Modal>
  );
}

const BRIEF_FIELDS: { key: keyof Brief; label: string }[] = [
  { key: 'context', label: 'Context' }, { key: 'goal', label: 'Goal' },
  { key: 'deliverables', label: 'Deliverables' }, { key: 'out', label: 'Out of scope' },
];

function ProjectDetail({ project }: { project: Project }) {
  const { clients, refresh } = useData();
  const toast = useToast();
  const nav = useNavigate();

  async function patch(body: Record<string, unknown>) {
    try {
      await api.patch(`/projects/${project.id}`, body);
      await refresh('projects');
    } catch (e) { toast.fail(e); }
  }
  async function remove() {
    try {
      await api.del(`/projects/${project.id}`);
      await refresh('projects', 'tasks');
      nav('/projects');
    } catch (e) { toast.fail(e); }
  }

  return (
    <div className="stack">
      <header className="page-head">
        <input className="title-input" defaultValue={project.name} maxLength={200} aria-label="Project name"
          onBlur={(e) => { const v = e.target.value.trim(); if (v && v !== project.name) void patch({ name: v }); }} />
        <div className="row">
          <Field label="Status">
            <select value={project.status} onChange={(e) => void patch({ status: e.target.value as ProjectStatus })}>
              {PROJECT_STATUSES.map((s) => <option key={s}>{s}</option>)}
            </select>
          </Field>
          <Field label="Client">
            <select value={project.client_id ?? ''} onChange={(e) => void patch({ client_id: e.target.value || null })}>
              <option value="">None</option>
              {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </Field>
          <Field label="Start"><input type="date" defaultValue={project.start ?? ''} onBlur={(e) => void patch({ start: e.target.value || null })} /></Field>
          <Field label="Deadline"><input type="date" defaultValue={project.deadline ?? ''} onBlur={(e) => void patch({ deadline: e.target.value || null })} /></Field>
        </div>
      </header>

      <section className="panel">
        <h2 className="section">Brief</h2>
        <div className="grid2">
          {BRIEF_FIELDS.map(({ key, label }) => (
            <Field key={key} label={label}>
              <textarea rows={4} defaultValue={project.brief[key]} maxLength={20000}
                onBlur={(e) => { if (e.target.value !== project.brief[key]) void patch({ brief: { [key]: e.target.value } }); }} />
            </Field>
          ))}
        </div>
      </section>

      <Journal projectId={project.id} />
      <footer className="end"><DeleteButton onConfirm={remove} label="Delete project" /></footer>
    </div>
  );
}

function Journal({ projectId }: { projectId: string }) {
  const toast = useToast();
  const [notes, setNotes] = useState<Note[]>([]);
  const [kind, setKind] = useState<NoteKind>('note');
  const [date, setDate] = useState(isoToday());
  const [body, setBody] = useState('');

  const load = () => api.get<Note[]>(`/projects/${projectId}/notes`).then(setNotes).catch(toast.fail);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { void load(); }, [projectId]);

  async function add(e: FormEvent) {
    e.preventDefault();
    try {
      await api.post(`/projects/${projectId}/notes`, { kind, date, body });
      setBody('');
      await load();
    } catch (err) { toast.fail(err); }
  }
  async function remove(id: string) {
    try { await api.del(`/notes/${id}`); await load(); } catch (err) { toast.fail(err); }
  }

  return (
    <section className="panel">
      <h2 className="section">Journal</h2>
      <form className="form inline" onSubmit={add}>
        <select value={kind} onChange={(e) => setKind(e.target.value as NoteKind)} aria-label="Entry type">
          {NOTE_KINDS.map((k) => <option key={k.key} value={k.key}>{k.label}</option>)}
        </select>
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} aria-label="Date" required />
        <input className="grow" placeholder="Call, decision, feedback…" value={body} onChange={(e) => setBody(e.target.value)} maxLength={20000} aria-label="Entry text" />
        <button className="primary" disabled={!body.trim()}>Add</button>
      </form>
      {notes.length === 0 && <Empty>No entries yet.</Empty>}
      <ul className="journal">
        {notes.map((n) => (
          <li key={n.id}>
            <div className="head"><span className="tag">{NOTE_KINDS.find((k) => k.key === n.kind)?.label}</span><small>{formatDate(n.date)}</small>
              <button className="icon" aria-label="Delete entry" onClick={() => void remove(n.id)}>×</button></div>
            <p>{n.body}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
