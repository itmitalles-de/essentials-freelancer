from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.billing_policy import (
    BillingDecision,
    BillingPolicyError,
    apply_billing_decision,
    calculate_billing_decision,
    recalculate_billable_minutes,
)
from app.database import get_db
from app.deps import get_current_user, require_module
from app.idempotency import request_fingerprint
from app.models import Client, CompanySettings, Project, TimeEntry, User
from app.schemas import (
    TimeEntryCreate,
    TimeEntryOut,
    TimeEntryStart,
    TimeEntryUpdate,
)
from app.time_utils import utc_now_naive

router = APIRouter(
    prefix="/api/time-entries",
    tags=["time-entries"],
    dependencies=[Depends(require_module("core.time_tracking"))],
)


def _project_for_client(
    db: Session, project_id: int | None, client_id: int, *, require_active: bool = True
) -> Project | None:
    if project_id is None:
        return None
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    if project.client_id != client_id:
        raise HTTPException(
            status_code=400, detail="Projekt gehört nicht zu diesem Kunden"
        )
    if require_active and not project.active:
        raise HTTPException(status_code=400, detail="Projekt ist archiviert")
    return project


def _company_settings(db: Session) -> CompanySettings:
    company = db.get(CompanySettings, 1)
    if company is None:
        company = CompanySettings(id=1)
        db.add(company)
        db.flush()
    return company


def _decision(
    *,
    db: Session,
    client: Client,
    project: Project | None,
    actual_minutes: int,
    travel_actual_minutes: int,
    is_first_order: bool,
    service_mode: str | None,
    explicit_hourly_rate: Decimal | None,
) -> BillingDecision:
    try:
        return calculate_billing_decision(
            actual_minutes=actual_minutes,
            travel_actual_minutes=travel_actual_minutes,
            is_first_order=is_first_order,
            requested_service_mode=service_mode,
            client=client,
            project=project,
            company=_company_settings(db),
            explicit_hourly_rate=explicit_hourly_rate,
        )
    except BillingPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[TimeEntryOut])
def list_time_entries(
    response: Response,
    client_id: int | None = None,
    project_id: int | None = None,
    billed: bool | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(TimeEntry)
    if client_id is not None:
        query = query.filter(TimeEntry.client_id == client_id)
    if project_id is not None:
        query = query.filter(TimeEntry.project_id == project_id)
    if billed is not None:
        query = query.filter(TimeEntry.billed == billed)
    if date_from is not None:
        query = query.filter(TimeEntry.date >= date_from)
    if date_to is not None:
        query = query.filter(TimeEntry.date <= date_to)
    response.headers["X-Total-Count"] = str(query.count())
    return (
        query.order_by(TimeEntry.date.desc(), TimeEntry.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.post("", response_model=TimeEntryOut)
def create_time_entry(
    payload: TimeEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = db.get(Client, payload.client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")
    data = payload.model_dump()
    project = _project_for_client(db, data["project_id"], client.id)
    explicit_rate = (
        Decimal(data["hourly_rate"]) if data["hourly_rate"] is not None else None
    )
    decision = _decision(
        db=db,
        client=client,
        project=project,
        actual_minutes=data["duration_minutes"],
        travel_actual_minutes=data.pop("travel_actual_minutes"),
        is_first_order=data.pop("is_first_order"),
        service_mode=data.pop("service_mode"),
        explicit_hourly_rate=explicit_rate,
    )
    data.pop("hourly_rate")
    entry = TimeEntry(**data, hourly_rate=decision.hourly_rate)
    apply_billing_decision(entry, decision)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.put("/{entry_id}", response_model=TimeEntryOut)
def update_time_entry(
    entry_id: int,
    payload: TimeEntryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = db.get(TimeEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")
    if entry.billed:
        raise HTTPException(
            status_code=400, detail="Bereits abgerechnete Einträge können nicht geändert werden"
        )
    changes = payload.model_dump(exclude_unset=True)
    if "project_id" in changes:
        _project_for_client(db, changes["project_id"], entry.client_id)
    for key, value in changes.items():
        setattr(entry, key, value)
    billing_fields = {
        "project_id",
        "duration_minutes",
        "hourly_rate",
        "service_mode",
        "is_first_order",
        "travel_actual_minutes",
    }
    if billing_fields.intersection(changes):
        client = db.get(Client, entry.client_id)
        project = _project_for_client(db, entry.project_id, entry.client_id)
        explicit_rate = None
        if "hourly_rate" in changes and changes["hourly_rate"] is not None:
            explicit_rate = Decimal(changes["hourly_rate"])
        elif (
            "hourly_rate" not in changes
            and entry.billing_rate_source == "time_entry_override"
        ):
            explicit_rate = Decimal(entry.hourly_rate)
        decision = _decision(
            db=db,
            client=client,
            project=project,
            actual_minutes=entry.duration_minutes,
            travel_actual_minutes=entry.travel_actual_minutes,
            is_first_order=entry.is_first_order,
            service_mode=entry.service_mode,
            explicit_hourly_rate=explicit_rate,
        )
        apply_billing_decision(entry, decision)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=204)
def delete_time_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = db.get(TimeEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")
    if entry.billed:
        raise HTTPException(
            status_code=400, detail="Bereits abgerechnete Einträge können nicht gelöscht werden"
        )
    db.delete(entry)
    db.commit()


@router.post("/start", response_model=TimeEntryOut)
def start_timer(
    payload: TimeEntryStart,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    fingerprint = request_fingerprint(payload.model_dump(mode="json"))
    if idempotency_key is not None:
        idempotency_key = idempotency_key.strip()
        if not idempotency_key or len(idempotency_key) > 128:
            raise HTTPException(status_code=400, detail="Ungültiger Idempotency-Key")
        existing = (
            db.query(TimeEntry)
            .filter(TimeEntry.start_request_key == idempotency_key)
            .first()
        )
        if existing is not None:
            if existing.start_request_fingerprint != fingerprint:
                raise HTTPException(
                    status_code=409,
                    detail="Idempotency-Key wurde bereits für andere Eingabedaten verwendet",
                )
            return existing
    client = db.get(Client, payload.client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")
    project = _project_for_client(db, payload.project_id, client.id)
    running = (
        db.query(TimeEntry).filter(TimeEntry.running_started_at.isnot(None)).first()
    )
    if running is not None:
        if idempotency_key is not None and running.start_request_key == idempotency_key:
            return running
        raise HTTPException(
            status_code=400, detail="Es läuft bereits ein Timer, zuerst stoppen"
        )
    now = utc_now_naive()
    decision = _decision(
        db=db,
        client=client,
        project=project,
        actual_minutes=0,
        travel_actual_minutes=payload.travel_actual_minutes,
        is_first_order=payload.is_first_order,
        service_mode=payload.service_mode.value if payload.service_mode else None,
        explicit_hourly_rate=None,
    )
    entry = TimeEntry(
        client_id=client.id,
        project_id=payload.project_id,
        date=now.date(),
        description=payload.description,
        duration_minutes=0,
        hourly_rate=decision.hourly_rate,
        running_started_at=now,
        start_request_key=idempotency_key,
        start_request_fingerprint=fingerprint if idempotency_key else None,
    )
    apply_billing_decision(entry, decision)
    db.add(entry)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if idempotency_key is not None:
            existing = (
                db.query(TimeEntry)
                .filter(TimeEntry.start_request_key == idempotency_key)
                .first()
            )
            if existing is not None:
                if existing.start_request_fingerprint != fingerprint:
                    raise HTTPException(
                        status_code=409,
                        detail="Idempotency-Key wurde bereits für andere Eingabedaten verwendet",
                    )
                return existing
        raise HTTPException(
            status_code=400, detail="Es läuft bereits ein Timer, zuerst stoppen"
        )
    db.refresh(entry)
    return entry


@router.post("/{entry_id}/stop", response_model=TimeEntryOut)
def stop_timer(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = (
        db.query(TimeEntry)
        .filter(TimeEntry.id == entry_id)
        .with_for_update()
        .one_or_none()
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")
    if entry.running_started_at is None:
        return entry
    elapsed = utc_now_naive() - entry.running_started_at
    entry.duration_minutes += max(1, round(elapsed.total_seconds() / 60))
    entry.billable_minutes = recalculate_billable_minutes(
        actual_minutes=entry.duration_minutes,
        minimum_minutes=entry.applied_minimum_minutes or 0,
        increment_minutes=entry.applied_increment_minutes,
    )
    entry.running_started_at = None
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/running", response_model=TimeEntryOut | None)
def get_running(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return (
        db.query(TimeEntry).filter(TimeEntry.running_started_at.isnot(None)).first()
    )
