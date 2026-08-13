from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_module
from app.models import Client, Invoice, Project, Quote, TimeEntry, User
from app.schemas import ClientCreate, ClientOut

router = APIRouter(
    prefix="/api/clients",
    tags=["clients"],
    dependencies=[Depends(require_module("core.clients"))],
)


@router.get("", response_model=list[ClientOut])
def list_clients(
    response: Response,
    q: str | None = None,
    active: bool | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    query = db.query(Client)
    if q:
        query = query.filter(Client.name.ilike(f"%{q.strip()}%"))
    if active is not None:
        query = query.filter(Client.active == active)
    response.headers["X-Total-Count"] = str(query.count())
    return query.order_by(Client.name).offset(offset).limit(limit).all()


@router.post("", response_model=ClientOut)
def create_client(
    payload: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = Client(**payload.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.get("/{client_id}", response_model=ClientOut)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")
    return client


@router.put("/{client_id}", response_model=ClientOut)
def update_client(
    client_id: int,
    payload: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")
    for key, value in payload.model_dump().items():
        setattr(client, key, value)
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=204)
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")
    has_time_entries = (
        db.query(TimeEntry).filter(TimeEntry.client_id == client_id).first() is not None
    )
    has_invoices = (
        db.query(Invoice).filter(Invoice.client_id == client_id).first() is not None
    )
    has_projects = (
        db.query(Project).filter(Project.client_id == client_id).first() is not None
    )
    has_quotes = db.query(Quote).filter(Quote.client_id == client_id).first() is not None
    if has_time_entries or has_invoices or has_projects or has_quotes:
        raise HTTPException(
            status_code=400,
            detail="Kunde hat Projekte, Zeiteinträge, Angebote oder Rechnungen und kann nicht gelöscht werden. Stattdessen inaktiv setzen.",
        )
    db.delete(client)
    db.commit()
