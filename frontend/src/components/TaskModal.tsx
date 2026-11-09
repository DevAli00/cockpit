import { useState, type FormEvent } from 'react';
import { api } from '../lib/api';
import { COLUMNS } from '../lib/constants';
import { useData } from '../lib/data';
import { useToast } from '../lib/toast';
import type { Task, TaskColumn } from '../types';
import { DeleteButton, Field, Modal } from './ui';

/** Create (task = null) or edit a task. */
export function TaskModal({ task, defaultCol, onClose }: { task: Task | null; defaultCol?: TaskColumn; onClose: () => void }) {
  const { clients, projects, refresh } = useData();
  const toast = useToast();
  const [title, setTitle] = useState(task?.title ?? '');
  const [clientId, setClientId] = useState(task?.client_id ?? '');
  const [projectId, setProjectId] = useState(task?.project_id ?? '');
  const [due, setDue] = useState(task?.due ?? '');
  const [note, setNote] = useState(task?.note ?? '');
  const [busy, setBusy] = useState(false);

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    const body = { title, client_id: clientId || null, project_id: projectId || null, due: due || null, note };
    try {
      if (task) await api.patch(`/tasks/${task.id}`, body);
      else await api.post('/tasks', { ...body, col: defaultCol ?? 'todo' });
      await refresh('tasks');
      onClose();
    } catch (err) {
      toast.fail(err);
      setBusy(false);
    }
  }

  async function remove() {
    if (!task) return;
    try {
      await api.del(`/tasks/${task.id}`);
      await refresh('tasks');
      onClose();
    } catch (err) {
      toast.fail(err);
    }
  }

  return (
    <Modal title={task ? 'Edit task' : 'New task'} onClose={onClose}>
      <form onSubmit={save} className="form">
        <Field label="Title"><input value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={300} /></Field>
        <div className="row">
          <Field label="Client">
            <select value={clientId} onChange={(e) => setClientId(e.target.value)}>
              <option value="">None</option>
              {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </Field>
          <Field label="Project">
            <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              <option value="">None</option>
              {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </Field>
          <Field label="Due"><input type="date" value={due} onChange={(e) => setDue(e.target.value)} /></Field>
        </div>
        <Field label="Notes"><textarea rows={4} value={note} onChange={(e) => setNote(e.target.value)} maxLength={20000} /></Field>
        <footer>
          {task && <DeleteButton onConfirm={remove} />}
          <span className="spacer" />
          <button type="button" onClick={onClose}>Cancel</button>
          <button className="primary" disabled={busy || !title.trim()}>Save</button>
        </footer>
        {task && <p className="hint">Column: {COLUMNS.find((c) => c.key === task.col)?.label}. Drag the card to move it.</p>}
      </form>
    </Modal>
  );
}
