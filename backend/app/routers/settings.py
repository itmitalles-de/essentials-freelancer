import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings as app_settings
from app.database import get_db
from app.deps import get_current_user
from app.models import CompanySettings, User
from app.schemas import CompanySettingsOut, CompanySettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])

ALLOWED_LOGO_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
}
MAX_LOGO_SIZE = 5 * 1024 * 1024


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
    return CompanySettingsOut.from_model(_get_or_create(db))


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
    return CompanySettingsOut.from_model(company)


@router.post("/logo", response_model=CompanySettingsOut)
async def upload_logo(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    extension = ALLOWED_LOGO_TYPES.get(file.content_type)
    if extension is None:
        raise HTTPException(
            status_code=400, detail="Nur PNG- oder JPEG-Bilder sind als Logo erlaubt"
        )
    content = await file.read()
    if len(content) > MAX_LOGO_SIZE:
        raise HTTPException(status_code=400, detail="Logo darf maximal 5 MB groß sein")

    company = _get_or_create(db)
    os.makedirs(app_settings.pdf_storage_dir, exist_ok=True)

    if company.logo_path and os.path.exists(company.logo_path):
        os.remove(company.logo_path)

    file_name = f"logo-{uuid.uuid4().hex}{extension}"
    file_path = os.path.join(app_settings.pdf_storage_dir, file_name)
    with open(file_path, "wb") as f:
        f.write(content)

    company.logo_path = file_path
    db.commit()
    db.refresh(company)
    return CompanySettingsOut.from_model(company)


@router.get("/logo")
def download_logo(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    company = _get_or_create(db)
    if not company.logo_path or not os.path.exists(company.logo_path):
        raise HTTPException(status_code=404, detail="Kein Logo hinterlegt")
    return FileResponse(company.logo_path)


@router.delete("/logo", response_model=CompanySettingsOut)
def delete_logo(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    company = _get_or_create(db)
    if company.logo_path and os.path.exists(company.logo_path):
        os.remove(company.logo_path)
    company.logo_path = None
    db.commit()
    db.refresh(company)
    return CompanySettingsOut.from_model(company)
