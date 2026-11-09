"""Authenticated resource routes. Thin: parse, call a service, shape the response."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select

from app.api.deps import Session, current_user
from app.db.models import Client, Entry, Note, Project, Recurring, Task
from app.domain.finance import Period
from app.schemas import (
    ClientIn, ClientOut, ClientPatch, EntryIn, EntryOut, EntryPatch, FinanceSummary,
    NoteIn, NoteOut, NotePatch, ProfileIn, ProfileOut, ProjectIn, ProjectOut, ProjectPatch,
    RecurringIn, RecurringOut, RecurringPatch, Scope, SearchHit, TaskIn, TaskMoveIn, TaskOut, TaskPatch,
)
from app.schemas_backup import Backup
from app.services import backup, crud, finance, profile, projects, search, tasks

router = APIRouter(dependencies=[Depends(current_user)])
NO_CONTENT = status.HTTP_204_NO_CONTENT


# --- clients ----------------------------------------------------------------------------------
@router.get("/clients", response_model=list[ClientOut])
async def list_clients(s: Session) -> list[Client]:
    return await crud.list_all(s, Client, Client.name, Client.id)


@router.post("/clients", response_model=ClientOut, status_code=201)
async def create_client(body: ClientIn, s: Session) -> Client:
    return await crud.create(s, Client, body.model_dump())


@router.get("/clients/{id}", response_model=ClientOut)
async def get_client(id: uuid.UUID, s: Session) -> Client:
    return await crud.get_or_404(s, Client, id)


@router.patch("/clients/{id}", response_model=ClientOut)
async def patch_client(id: uuid.UUID, body: ClientPatch, s: Session) -> Client:
    return await crud.update(s, await crud.get_or_404(s, Client, id), body.model_dump(exclude_unset=True))


@router.delete("/clients/{id}", status_code=NO_CONTENT)
async def delete_client(id: uuid.UUID, s: Session) -> None:
    await crud.delete(s, await crud.get_or_404(s, Client, id))


# --- projects & journal -----------------------------------------------------------------------
@router.get("/projects", response_model=list[ProjectOut])
async def list_projects(s: Session) -> list[Project]:
    return await crud.list_all(s, Project, Project.position, Project.id)


@router.post("/projects", response_model=ProjectOut, status_code=201)
async def create_project(body: ProjectIn, s: Session) -> Project:
    return await projects.create_project(s, body.model_dump())


@router.get("/projects/{id}", response_model=ProjectOut)
async def get_project(id: uuid.UUID, s: Session) -> Project:
    return await crud.get_or_404(s, Project, id)


@router.patch("/projects/{id}", response_model=ProjectOut)
async def patch_project(id: uuid.UUID, body: ProjectPatch, s: Session) -> Project:
    return await projects.update_project(
        s, await crud.get_or_404(s, Project, id), body.model_dump(exclude_unset=True)
    )


@router.delete("/projects/{id}", status_code=NO_CONTENT)
async def delete_project(id: uuid.UUID, s: Session) -> None:
    await crud.delete(s, await crud.get_or_404(s, Project, id))


@router.get("/projects/{id}/notes", response_model=list[NoteOut])
async def list_notes(id: uuid.UUID, s: Session) -> list[Note]:
    await crud.get_or_404(s, Project, id)
    stmt = select(Note).where(Note.project_id == id).order_by(Note.date.desc(), Note.created_at.desc())
    return list((await s.scalars(stmt)).all())


@router.post("/projects/{id}/notes", response_model=NoteOut, status_code=201)
async def create_note(id: uuid.UUID, body: NoteIn, s: Session) -> Note:
    await crud.get_or_404(s, Project, id)
    return await crud.create(s, Note, {**body.model_dump(), "project_id": id})


@router.patch("/notes/{id}", response_model=NoteOut)
async def patch_note(id: uuid.UUID, body: NotePatch, s: Session) -> Note:
    return await crud.update(s, await crud.get_or_404(s, Note, id), body.model_dump(exclude_unset=True))


@router.delete("/notes/{id}", status_code=NO_CONTENT)
async def delete_note(id: uuid.UUID, s: Session) -> None:
    await crud.delete(s, await crud.get_or_404(s, Note, id))


# --- tasks ------------------------------------------------------------------------------------
@router.get("/tasks", response_model=list[TaskOut])
async def list_tasks(s: Session, include_archived: bool = False) -> list[Task]:
    return await tasks.list_tasks(s, include_archived=include_archived)


@router.post("/tasks", response_model=TaskOut, status_code=201)
async def create_task(body: TaskIn, s: Session) -> Task:
    return await tasks.create_task(s, body.model_dump())


@router.get("/tasks/{id}", response_model=TaskOut)
async def get_task(id: uuid.UUID, s: Session) -> Task:
    return await crud.get_or_404(s, Task, id)


@router.patch("/tasks/{id}", response_model=TaskOut)
async def patch_task(id: uuid.UUID, body: TaskPatch, s: Session) -> Task:
    return await crud.update(s, await crud.get_or_404(s, Task, id), body.model_dump(exclude_unset=True))


@router.post("/tasks/{id}/move", response_model=TaskOut)
async def move_task(id: uuid.UUID, body: TaskMoveIn, s: Session) -> Task:
    return await tasks.move_task(s, id, body.col, body.before_id)


@router.delete("/tasks/{id}", status_code=NO_CONTENT)
async def delete_task(id: uuid.UUID, s: Session) -> None:
    await crud.delete(s, await crud.get_or_404(s, Task, id))


# --- finance ----------------------------------------------------------------------------------
@router.get("/entries", response_model=list[EntryOut])
async def list_entries(s: Session, scope: Scope | None = None) -> list[Entry]:
    stmt = select(Entry).order_by(Entry.date.desc(), Entry.id)
    if scope:
        stmt = stmt.where(Entry.scope == scope)
    return list((await s.scalars(stmt)).all())


@router.post("/entries", response_model=EntryOut, status_code=201)
async def create_entry(body: EntryIn, s: Session) -> Entry:
    return await crud.create(s, Entry, body.model_dump())


@router.patch("/entries/{id}", response_model=EntryOut)
async def patch_entry(id: uuid.UUID, body: EntryPatch, s: Session) -> Entry:
    return await crud.update(s, await crud.get_or_404(s, Entry, id), body.model_dump(exclude_unset=True))


@router.delete("/entries/{id}", status_code=NO_CONTENT)
async def delete_entry(id: uuid.UUID, s: Session) -> None:
    await crud.delete(s, await crud.get_or_404(s, Entry, id))


@router.get("/recurring", response_model=list[RecurringOut])
async def list_recurring(s: Session, scope: Scope | None = None) -> list[Recurring]:
    stmt = select(Recurring).order_by(Recurring.start.desc(), Recurring.id)
    if scope:
        stmt = stmt.where(Recurring.scope == scope)
    return list((await s.scalars(stmt)).all())


@router.post("/recurring", response_model=RecurringOut, status_code=201)
async def create_recurring(body: RecurringIn, s: Session) -> Recurring:
    return await crud.create(s, Recurring, body.model_dump())


@router.patch("/recurring/{id}", response_model=RecurringOut)
async def patch_recurring(id: uuid.UUID, body: RecurringPatch, s: Session) -> Recurring:
    return await crud.update(s, await crud.get_or_404(s, Recurring, id), body.model_dump(exclude_unset=True))


@router.delete("/recurring/{id}", status_code=NO_CONTENT)
async def delete_recurring(id: uuid.UUID, s: Session) -> None:
    await crud.delete(s, await crud.get_or_404(s, Recurring, id))


@router.get("/finance/summary", response_model=FinanceSummary)
async def finance_summary(
    s: Session, period: Period = "month", scope: Literal["business", "personal", "all"] = "business"
) -> FinanceSummary:
    return await finance.summarize(s, period, date.today(), scope)


# --- profile, search, backup ------------------------------------------------------------------
@router.get("/profile", response_model=ProfileOut)
async def get_profile(s: Session) -> object:
    return await profile.get_profile(s)


@router.put("/profile", response_model=ProfileOut)
async def put_profile(body: ProfileIn, s: Session) -> object:
    return await profile.update_profile(s, body.model_dump())


@router.get("/search", response_model=list[SearchHit])
async def global_search(s: Session, q: Annotated[str, Query(min_length=2, max_length=100)]) -> list[SearchHit]:
    return await search.search(s, q)


@router.get("/backup", response_model=Backup)
async def export_backup(s: Session) -> Backup:
    return await backup.export_all(s)


@router.post("/backup", status_code=NO_CONTENT)
async def import_backup(body: Backup, s: Session) -> None:
    await backup.import_all(s, body)
