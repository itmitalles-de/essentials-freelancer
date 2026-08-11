import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
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
    if expense.receipt_path and os.path.exists(expense.receipt_path):
        os.remove(expense.receipt_path)
    db.delete(expense)
    db.commit()


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

    os.makedirs(app_settings.pdf_storage_dir, exist_ok=True)
    if expense.receipt_path and os.path.exists(expense.receipt_path):
        os.remove(expense.receipt_path)

    file_name = f"receipt-{uuid.uuid4().hex}{extension}"
    file_path = os.path.join(app_settings.pdf_storage_dir, file_name)
    with open(file_path, "wb") as f:
        f.write(content)

    expense.receipt_path = file_path
    db.commit()
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
