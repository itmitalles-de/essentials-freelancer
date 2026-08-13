import os
import uuid
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.config import settings as app_settings
from app.database import get_db
from app.deps import get_current_user
from app.models import Expense, User
from app.schemas import ExpenseCreate, ExpenseOut

router = APIRouter(prefix="/api/expenses", tags=["expenses"])

ALLOWED_RECEIPT_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "application/pdf": ".pdf",
}
MAX_RECEIPT_SIZE = 5 * 1024 * 1024


def _validate_receipt_content(content: bytes, content_type: str) -> None:
    if content_type == "application/pdf":
        if not content.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail="Der Beleg ist keine gültige PDF-Datei")
        return
    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="Der Beleg ist keine gültige Bilddatei")


@router.get("", response_model=list[ExpenseOut])
def list_expenses(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    expenses = db.query(Expense).order_by(Expense.date.desc()).all()
    return [ExpenseOut.from_model(e) for e in expenses]


@router.post("", response_model=ExpenseOut)
def create_expense(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    expense = Expense(**payload.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return ExpenseOut.from_model(expense)


@router.put("/{expense_id}", response_model=ExpenseOut)
def update_expense(
    expense_id: int,
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(status_code=404, detail="Ausgabe nicht gefunden")
    for key, value in payload.model_dump().items():
        setattr(expense, key, value)
    db.commit()
    db.refresh(expense)
    return ExpenseOut.from_model(expense)


@router.delete("/{expense_id}", status_code=204)
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(status_code=404, detail="Ausgabe nicht gefunden")
    receipt_path = expense.receipt_path
    db.delete(expense)
    db.commit()
    if receipt_path:
        try:
            os.remove(receipt_path)
        except FileNotFoundError:
            pass


@router.post("/{expense_id}/receipt", response_model=ExpenseOut)
async def upload_receipt(
    expense_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(status_code=404, detail="Ausgabe nicht gefunden")

    extension = ALLOWED_RECEIPT_TYPES.get(file.content_type)
    if extension is None:
        raise HTTPException(
            status_code=400, detail="Nur PNG, JPEG oder PDF sind als Beleg erlaubt"
        )
    content = await file.read()
    if len(content) > MAX_RECEIPT_SIZE:
        raise HTTPException(status_code=400, detail="Beleg darf maximal 5 MB groß sein")
    _validate_receipt_content(content, file.content_type or "")

    os.makedirs(app_settings.pdf_storage_dir, exist_ok=True)
    old_path = expense.receipt_path
    file_name = f"receipt-{uuid.uuid4().hex}{extension}"
    file_path = os.path.join(app_settings.pdf_storage_dir, file_name)
    temporary_path = f"{file_path}.tmp"
    try:
        with open(temporary_path, "xb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary_path, file_path)
        expense.receipt_path = file_path
        db.commit()
    except Exception:
        db.rollback()
        for path in (temporary_path, file_path):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
        raise
    if old_path and old_path != file_path:
        try:
            os.remove(old_path)
        except FileNotFoundError:
            pass
    db.refresh(expense)
    return ExpenseOut.from_model(expense)


@router.get("/{expense_id}/receipt")
def download_receipt(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(status_code=404, detail="Ausgabe nicht gefunden")
    if not expense.receipt_path or not os.path.exists(expense.receipt_path):
        raise HTTPException(status_code=404, detail="Kein Beleg hinterlegt")
    return FileResponse(expense.receipt_path)
