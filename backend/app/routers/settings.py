from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import CompanySettings, User
from app.schemas import CompanySettingsOut, CompanySettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _get_or_create(db: Session) -> CompanySettings:
    company = db.get(CompanySettings, 1)
    if company is None:
        company = CompanySettings(id=1)
        db.add(company)
        db.commit()
        db.refresh(company)
    return company


@router.get("", response_model=CompanySettingsOut)
def get_settings(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return _get_or_create(db)


@router.put("", response_model=CompanySettingsOut)
def update_settings(
    payload: CompanySettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = _get_or_create(db)
    for key, value in payload.model_dump().items():
        setattr(company, key, value)
    db.commit()
    db.refresh(company)
    return company
