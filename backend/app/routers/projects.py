from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_module
from app.models import Client, InvoiceLineItem, Project, Quote, TimeEntry, User
from app.schemas import ProjectCreate, ProjectOut

router = APIRouter(
    prefix="/api/projects",
    tags=["projects"],
    dependencies=[Depends(require_module("core.projects"))],
)


def _client_or_404(db: Session, client_id: int) -> Client:
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")
    return client


def _unique_name_or_400(
    db: Session, client_id: int, name: str, excluding_id: int | None = None
) -> None:
    query = db.query(Project).filter(
        Project.client_id == client_id,
        Project.name == name,
    )
    if excluding_id is not None:
        query = query.filter(Project.id != excluding_id)
    if query.first() is not None:
        raise HTTPException(
            status_code=400,
            detail="Für diesen Kunden existiert bereits ein Projekt mit diesem Namen",
        )


@router.get("", response_model=list[ProjectOut])
def list_projects(
    response: Response,
    client_id: int | None = None,
    active: bool | None = None,
    q: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Project)
    if client_id is not None:
        query = query.filter(Project.client_id == client_id)
    if active is not None:
        query = query.filter(Project.active == active)
    if q:
        query = query.filter(Project.name.ilike(f"%{q.strip()}%"))
    response.headers["X-Total-Count"] = str(query.count())
    return (
        query.order_by(Project.active.desc(), Project.name)
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.post("", response_model=ProjectOut)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _client_or_404(db, payload.client_id)
    _unique_name_or_400(db, payload.client_id, payload.name)
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return project


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    _client_or_404(db, payload.client_id)
    if payload.client_id != project.client_id:
        has_links = (
            db.query(TimeEntry).filter(TimeEntry.project_id == project_id).first()
            is not None
            or db.query(Quote).filter(Quote.project_id == project_id).first() is not None
            or db.query(InvoiceLineItem)
            .filter(InvoiceLineItem.project_id == project_id)
            .first()
            is not None
        )
        if has_links:
            raise HTTPException(
                status_code=400,
                detail="Ein verknüpftes Projekt kann nicht zu einem anderen Kunden verschoben werden",
            )
    _unique_name_or_400(db, payload.client_id, payload.name, project_id)
    for key, value in payload.model_dump().items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    has_links = (
        db.query(TimeEntry).filter(TimeEntry.project_id == project_id).first()
        is not None
        or db.query(Quote).filter(Quote.project_id == project_id).first() is not None
        or db.query(InvoiceLineItem)
        .filter(InvoiceLineItem.project_id == project_id)
        .first()
        is not None
    )
    if has_links:
        raise HTTPException(
            status_code=400,
            detail="Projekt ist mit Zeiten, Angeboten oder Rechnungen verknüpft und kann nur archiviert werden",
        )
    db.delete(project)
    db.commit()
