from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Client, User
from app.schemas import ClientCreate, ClientOut

router = APIRouter(prefix="/api/clients", tags=["clients"])


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
    db.delete(client)
    db.commit()
