import { useRef, useState, type DragEvent } from 'react';
import { api } from '../lib/api';
import { COLUMNS } from '../lib/constants';
import { useData } from '../lib/data';
import { beforeIdAt, relativeDue } from '../lib/format';
import { useToast } from '../lib/toast';
import type { Task, TaskColumn } from '../types';
import { TaskModal } from './TaskModal';
import { Dot } from './ui';

export function Kanban() {
  const { tasks, setTasks, refresh, clientById, projectById } = useData();
  const toast = useToast();
  const dragged = useRef<string | null>(null);
  const [over, setOver] = useState<{ col: TaskColumn; index: number } | null>(null);
  const [editing, setEditing] = useState<{ task: Task | null; col?: TaskColumn } | null>(null);

  const byCol = (col: TaskColumn) => tasks.filter((t) => t.col === col);

  function indexFromPointer(e: DragEvent): number {
    const cards = [...e.currentTarget.querySelectorAll<HTMLElement>('[data-task]')];
    const i = cards.findIndex((c) => e.clientY < c.getBoundingClientRect().top + c.offsetHeight / 2);
    return i === -1 ? cards.length : i;
  }

  async function drop(col: TaskColumn, index: number) {
    const id = dragged.current;
    dragged.current = null;
    setOver(null);
    if (!id) return;
    const ids = byCol(col).map((t) => t.id);
    const beforeId = beforeIdAt(ids, index, id);
    // Optimistic: show the card in its new place now, reconcile with the server after.
    setTasks((cur) => {
      const moving = cur.find((t) => t.id === id);
      if (!moving) return cur;
      const rest = cur.filter((t) => t.id !== id);
      const at = beforeId ? rest.findIndex((t) => t.id === beforeId) : rest.length;
      return [...rest.slice(0, at), { ...moving, col }, ...rest.slice(at)];
    });
    try {
      await api.post(`/tasks/${id}/move`, { col, before_id: beforeId });
    } catch (e) {
      toast.fail(e);
    }
    await refresh('tasks');
  }

  return (
    <>
      <div className="board">
        {COLUMNS.map((col) => {
          const list = byCol(col.key);
          return (
            <section
              key={col.key}
              className={`column${over?.col === col.key ? ' over' : ''}`}
              onDragOver={(e) => { e.preventDefault(); setOver({ col: col.key, index: indexFromPointer(e) }); }}
              onDragLeave={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setOver(null); }}
              onDrop={(e) => { e.preventDefault(); void drop(col.key, indexFromPointer(e)); }}
            >
              <header>
                <h3><Dot color={col.dot} /> {col.label} <small>{list.length}</small></h3>
                <button className="icon" aria-label={`Add task to ${col.label}`} onClick={() => setEditing({ task: null, col: col.key })}>+</button>
              </header>
              {list.map((t, i) => {
                const client = clientById(t.client_id);
                const project = projectById(t.project_id);
                const due = t.due ? relativeDue(t.due) : null;
                return (
                  <article
                    key={t.id}
                    data-task
                    draggable
                    className={`card${over?.col === col.key && over.index === i ? ' drop-before' : ''}`}
                    style={{ borderLeftColor: client?.color ?? 'transparent' }}
                    onDragStart={(e) => {
                      dragged.current = t.id;
                      e.dataTransfer.effectAllowed = 'move';
                      e.dataTransfer.setData('text/plain', t.id); // some engines only start a drag with data set
                    }}
                    onDragEnd={() => { dragged.current = null; setOver(null); }}
                    onClick={() => setEditing({ task: t })}
                  >
                    <p>{t.title}</p>
                    <div className="meta">
                      {client && <span>{client.name}</span>}
                      {project && <span>{project.name}</span>}
                      {due && t.col !== 'done' && <span className={`due ${due.tone}`}>{due.text}</span>}
                    </div>
                  </article>
                );
              })}
              {list.length === 0 && <p className="empty small">Nothing here</p>}
            </section>
          );
        })}
      </div>
      {editing && <TaskModal task={editing.task} defaultCol={editing.col} onClose={() => setEditing(null)} />}
    </>
  );
}
