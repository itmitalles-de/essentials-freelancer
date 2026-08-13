from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_module
from app.models import ModuleAuditEvent, User
from app.module_registry import ModuleStatus
from app.module_service import disable_module, enable_module, list_module_statuses

router = APIRouter(
    prefix="/api/admin/modules",
    tags=["modules"],
    dependencies=[Depends(require_module("core.platform"))],
)


@router.get("", response_model=list[ModuleStatus])
def list_modules(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return list_module_statuses(db)


@router.post("/{module_id}/enable", response_model=ModuleStatus)
def enable(
    module_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return enable_module(db, module_id, current_user.username)


@router.post("/{module_id}/disable", response_model=ModuleStatus)
def disable(
    module_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return disable_module(db, module_id, current_user.username)


@router.get("/audit")
def audit_events(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    bounded_limit = min(max(limit, 1), 500)
    events = (
        db.query(ModuleAuditEvent)
        .order_by(ModuleAuditEvent.id.desc())
        .limit(bounded_limit)
        .all()
    )
    return [
        {
            "id": event.id,
            "module_id": event.module_id,
            "action": event.action,
            "previous_state": event.previous_state,
            "resulting_state": event.resulting_state,
            "actor": event.actor,
            "created_at": event.created_at,
        }
        for event in events
    ]
