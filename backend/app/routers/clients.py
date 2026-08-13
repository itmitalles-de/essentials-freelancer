from fastapi import APIRouter, Depends, HTTPException
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
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return db.query(Client).order_by(Client.name).all()


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
