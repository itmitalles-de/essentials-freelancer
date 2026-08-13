import json
import os
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings as app_settings
from app.database import get_db
from app.deps import get_current_user, require_module
from app.models import (
    AssistantDraftStatus,
    Client,
    Project,
    Quote,
    QuoteAssistantDraft,
    QuoteAssistantDraftLine,
    QuoteAssistantTemplate,
    QuoteAssistantTemplateSelection,
    QuoteAssistantTemplateVersion,
    QuoteCatalogItem,
    QuoteCatalogVersion,
    QuoteLineItem,
    QuotePackage,
    QuotePackageVersion,
    QuotePackageVersionItem,
    QuoteStatus,
    User,
)
from app.money import line_amounts, money
from app.pdf import generate_quote_pdf
from app.quote_assistant import (
    build_preview,
    calculate_preview,
    draft_out,
    package_out,
    template_out,
)
from app.routers.invoices import _get_or_create_settings
from app.schemas import (
    AssistantDraftCreate,
    AssistantDraftOut,
    AssistantPreviewOut,
    AssistantPreviewRequest,
    CatalogItemCreate,
    CatalogItemOut,
    CatalogVersionCreate,
    PackageCreate,
    PackageOut,
    PackageVersionCreate,
    TemplateCreate,
    TemplateOut,
    TemplateVersionCreate,
)
from app.time_utils import utc_now_naive

router = APIRouter(
    prefix="/api/quote-assistant",
    tags=["quote-assistant"],
    dependencies=[Depends(require_module("sales.quote_assistant"))],
)


def _conflict(code: str, message: str, **details) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={"code": code, "message": message, **details},
    )


def _client_project(
    db: Session, client_id: int, project_id: int | None
) -> tuple[Client, Project | None]:
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")
    project = db.get(Project, project_id) if project_id is not None else None
    if project_id is not None and project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    if project is not None and project.client_id != client.id:
        raise HTTPException(status_code=400, detail="Projekt gehört nicht zu diesem Kunden")
    if project is not None and not project.active:
        raise HTTPException(status_code=400, detail="Projekt ist archiviert")
    return client, project


def _commit_unique(db: Session, code: str, message: str) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _conflict(code, message)


@router.get("/catalog/items", response_model=list[CatalogItemOut])
def list_catalog_items(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    del current_user
    return db.query(QuoteCatalogItem).order_by(QuoteCatalogItem.name).all()


@router.post("/catalog/items", response_model=CatalogItemOut)
def create_catalog_item(
    payload: CatalogItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    if (
        db.query(QuoteCatalogItem)
        .filter(QuoteCatalogItem.stable_key == payload.stable_key)
        .first()
        is not None
    ):
        raise _conflict(
            "catalog_key_exists", "Die stabile Katalog-ID ist bereits vergeben."
        )
    item = QuoteCatalogItem(
        stable_key=payload.stable_key,
        kind=payload.kind,
        name=payload.name,
    )
    db.add(item)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise _conflict(
            "catalog_key_exists", "Die stabile Katalog-ID ist bereits vergeben."
        )
    item.versions.append(
        QuoteCatalogVersion(
            version=1,
            **payload.version.model_dump(),
        )
    )
    _commit_unique(
        db,
        "catalog_key_exists",
        "Die stabile Katalog-ID ist bereits vergeben.",
    )
    db.refresh(item)
    return item


@router.post("/catalog/items/{item_id}/versions", response_model=CatalogItemOut)
def add_catalog_version(
    item_id: int,
    payload: CatalogVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    item = (
        db.query(QuoteCatalogItem)
        .filter(QuoteCatalogItem.id == item_id)
        .with_for_update()
        .one_or_none()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Katalogposition nicht gefunden")
    latest = max(item.versions, key=lambda version: version.version)
    if payload.valid_from <= latest.valid_from:
        raise _conflict(
            "catalog_version_order",
            "Eine neue Katalogversion muss später beginnen als die letzte Version.",
        )
    if latest.valid_until is None or latest.valid_until >= payload.valid_from:
        latest.valid_until = payload.valid_from - timedelta(days=1)
    item.versions.append(
        QuoteCatalogVersion(
            version=latest.version + 1,
            **payload.model_dump(),
        )
    )
    _commit_unique(
        db,
        "catalog_version_conflict",
        "Die Katalogversion konnte wegen einer parallelen Änderung nicht angelegt werden.",
    )
    db.refresh(item)
    return item


def _append_package_version(
    db: Session,
    package: QuotePackage,
    payload: PackageVersionCreate,
    version_number: int,
) -> QuotePackageVersion:
    version = QuotePackageVersion(
        version=version_number,
        description=payload.description,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
    )
    package.versions.append(version)
    db.flush()
    for index, entry in enumerate(payload.items):
        if db.get(QuoteCatalogVersion, entry.catalog_version_id) is None:
            raise HTTPException(status_code=404, detail="Katalogversion nicht gefunden")
        version.items.append(
            QuotePackageVersionItem(
                catalog_version_id=entry.catalog_version_id,
                quantity=entry.quantity,
                sort_order=index,
            )
        )
    return version


@router.get("/packages", response_model=list[PackageOut])
def list_packages(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    del current_user
    return [
        package_out(item)
        for item in db.query(QuotePackage).order_by(QuotePackage.name).all()
    ]


@router.post("/packages", response_model=PackageOut)
def create_package(
    payload: PackageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    if (
        db.query(QuotePackage)
        .filter(QuotePackage.stable_key == payload.stable_key)
        .first()
        is not None
    ):
        raise _conflict(
            "package_key_exists", "Die stabile Paket-ID ist bereits vergeben."
        )
    package = QuotePackage(stable_key=payload.stable_key, name=payload.name)
    db.add(package)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise _conflict(
            "package_key_exists", "Die stabile Paket-ID ist bereits vergeben."
        )
    _append_package_version(db, package, payload.version, 1)
    _commit_unique(
        db,
        "package_key_exists",
        "Die stabile Paket-ID ist bereits vergeben.",
    )
    db.refresh(package)
    return package_out(package)


@router.post("/packages/{package_id}/versions", response_model=PackageOut)
def add_package_version(
    package_id: int,
    payload: PackageVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    package = (
        db.query(QuotePackage)
        .filter(QuotePackage.id == package_id)
        .with_for_update()
        .one_or_none()
    )
    if package is None:
        raise HTTPException(status_code=404, detail="Leistungspaket nicht gefunden")
    latest = max(package.versions, key=lambda version: version.version)
    if payload.valid_from <= latest.valid_from:
        raise _conflict(
            "package_version_order",
            "Eine neue Paketversion muss später beginnen als die letzte Version.",
        )
    if latest.valid_until is None or latest.valid_until >= payload.valid_from:
        latest.valid_until = payload.valid_from - timedelta(days=1)
    _append_package_version(db, package, payload, latest.version + 1)
    _commit_unique(
        db,
        "package_version_conflict",
        "Die Paketversion konnte wegen einer parallelen Änderung nicht angelegt werden.",
    )
    db.refresh(package)
    return package_out(package)


def _append_template_version(
    db: Session,
    template: QuoteAssistantTemplate,
    payload: TemplateVersionCreate,
    version_number: int,
) -> QuoteAssistantTemplateVersion:
    version = QuoteAssistantTemplateVersion(
        version=version_number,
        description=payload.description,
        questions_json=json.dumps(payload.questions, ensure_ascii=False),
        surcharge_percent=payload.surcharge_percent,
        discount_percent=payload.discount_percent,
    )
    template.versions.append(version)
    db.flush()
    for index, selection in enumerate(payload.selections):
        if selection.catalog_version_id is not None and db.get(
            QuoteCatalogVersion, selection.catalog_version_id
        ) is None:
            raise HTTPException(status_code=404, detail="Katalogversion nicht gefunden")
        if selection.package_version_id is not None and db.get(
            QuotePackageVersion, selection.package_version_id
        ) is None:
            raise HTTPException(status_code=404, detail="Paketversion nicht gefunden")
        version.selections.append(
            QuoteAssistantTemplateSelection(
                catalog_version_id=selection.catalog_version_id,
                package_version_id=selection.package_version_id,
                quantity=selection.quantity,
                sort_order=index,
            )
        )
    return version


@router.get("/templates", response_model=list[TemplateOut])
def list_templates(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    del current_user
    return [
        template_out(item)
        for item in db.query(QuoteAssistantTemplate)
        .order_by(QuoteAssistantTemplate.name)
        .all()
    ]


@router.post("/templates", response_model=TemplateOut)
def create_template(
    payload: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    if (
        db.query(QuoteAssistantTemplate)
        .filter(QuoteAssistantTemplate.stable_key == payload.stable_key)
        .first()
        is not None
    ):
        raise _conflict(
            "template_key_exists", "Die stabile Vorlagen-ID ist bereits vergeben."
        )
    template = QuoteAssistantTemplate(stable_key=payload.stable_key, name=payload.name)
    db.add(template)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise _conflict(
            "template_key_exists", "Die stabile Vorlagen-ID ist bereits vergeben."
        )
    _append_template_version(db, template, payload.version, 1)
    _commit_unique(
        db,
        "template_key_exists",
        "Die stabile Vorlagen-ID ist bereits vergeben.",
    )
    db.refresh(template)
    return template_out(template)


@router.post("/templates/{template_id}/versions", response_model=TemplateOut)
def add_template_version(
    template_id: int,
    payload: TemplateVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    template = (
        db.query(QuoteAssistantTemplate)
        .filter(QuoteAssistantTemplate.id == template_id)
        .with_for_update()
        .one_or_none()
    )
    if template is None:
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden")
    next_version = max(item.version for item in template.versions) + 1
    _append_template_version(db, template, payload, next_version)
    _commit_unique(
        db,
        "template_version_conflict",
        "Die Vorlagenversion konnte wegen einer parallelen Änderung nicht angelegt werden.",
    )
    db.refresh(template)
    return template_out(template)


@router.post("/preview", response_model=AssistantPreviewOut)
def preview(
    payload: AssistantPreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    return build_preview(db, payload)


def _apply_preview_to_draft(
    draft: QuoteAssistantDraft,
    payload: AssistantDraftCreate,
    preview: AssistantPreviewOut,
) -> None:
    draft.client_id = payload.client_id
    draft.project_id = payload.project_id
    draft.template_version_id = payload.template_version_id
    draft.title = payload.title
    draft.pricing_date = payload.pricing_date
    draft.guided_answers_json = json.dumps(
        payload.guided_answers, ensure_ascii=False, sort_keys=True
    )
    draft.notes = payload.notes
    draft.surcharge_percent = payload.surcharge_percent
    draft.discount_percent = payload.discount_percent
    draft.base_net_total = preview.base_net_total
    draft.surcharge_amount = preview.surcharge_amount
    draft.discount_amount = preview.discount_amount
    draft.net_total = preview.net_total
    draft.tax_total = preview.tax_total
    draft.total = preview.total
    draft.updated_at = utc_now_naive()
    draft.lines.clear()
    for line in preview.lines:
        draft.lines.append(QuoteAssistantDraftLine(**line.model_dump()))


def _validate_template(db: Session, template_version_id: int | None) -> None:
    if template_version_id is not None and db.get(
        QuoteAssistantTemplateVersion, template_version_id
    ) is None:
        raise HTTPException(status_code=404, detail="Vorlagenversion nicht gefunden")


@router.get("/drafts", response_model=list[AssistantDraftOut])
def list_drafts(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    del current_user
    return [
        draft_out(item)
        for item in db.query(QuoteAssistantDraft)
        .order_by(QuoteAssistantDraft.id.desc())
        .all()
    ]


@router.post("/drafts", response_model=AssistantDraftOut)
def create_draft(
    payload: AssistantDraftCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    _client_project(db, payload.client_id, payload.project_id)
    _validate_template(db, payload.template_version_id)
    preview_result = build_preview(db, payload)
    draft = QuoteAssistantDraft(status=AssistantDraftStatus.draft)
    _apply_preview_to_draft(draft, payload, preview_result)
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft_out(draft)


@router.get("/drafts/{draft_id}", response_model=AssistantDraftOut)
def get_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    draft = db.get(QuoteAssistantDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Assistentenentwurf nicht gefunden")
    return draft_out(draft)


@router.put("/drafts/{draft_id}", response_model=AssistantDraftOut)
def update_draft(
    draft_id: int,
    payload: AssistantDraftCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    draft = db.get(QuoteAssistantDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Assistentenentwurf nicht gefunden")
    if draft.status != AssistantDraftStatus.draft:
        raise _conflict(
            "draft_not_editable", "Nur ungeprüfte Entwürfe können geändert werden."
        )
    _client_project(db, payload.client_id, payload.project_id)
    _validate_template(db, payload.template_version_id)
    preview_result = build_preview(db, payload)
    _apply_preview_to_draft(draft, payload, preview_result)
    db.commit()
    db.refresh(draft)
    return draft_out(draft)


@router.post("/drafts/{draft_id}/approve", response_model=AssistantDraftOut)
def approve_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    draft = (
        db.query(QuoteAssistantDraft)
        .filter(QuoteAssistantDraft.id == draft_id)
        .with_for_update()
        .one_or_none()
    )
    if draft is None:
        raise HTTPException(status_code=404, detail="Assistentenentwurf nicht gefunden")
    if draft.status == AssistantDraftStatus.transferred:
        raise _conflict(
            "draft_already_transferred", "Der Entwurf wurde bereits in ein Angebot übernommen."
        )
    if draft.status == AssistantDraftStatus.draft:
        draft.status = AssistantDraftStatus.approved
        draft.approved_at = utc_now_naive()
        db.commit()
        db.refresh(draft)
    return draft_out(draft)


def _append_adjustment_lines(
    quote: Quote, draft: QuoteAssistantDraft, preview_result: AssistantPreviewOut
) -> None:
    for breakdown in preview_result.tax_breakdown:
        if breakdown.surcharge:
            net, tax, gross = line_amounts(
                Decimal("1"), breakdown.surcharge, breakdown.tax_rate
            )
            quote.line_items.append(
                QuoteLineItem(
                    description=f"Aufschlag {draft.surcharge_percent}%",
                    quantity=Decimal("1"),
                    unit="flat",
                    unit_price=breakdown.surcharge,
                    net_amount=net,
                    tax_rate=breakdown.tax_rate,
                    tax_amount=tax,
                    amount=gross,
                )
            )
        if breakdown.discount:
            net = -breakdown.discount
            tax = -money(breakdown.discount * breakdown.tax_rate / Decimal("100"))
            quote.line_items.append(
                QuoteLineItem(
                    description=f"Rabatt {draft.discount_percent}%",
                    quantity=Decimal("1"),
                    unit="flat",
                    unit_price=net,
                    net_amount=net,
                    tax_rate=breakdown.tax_rate,
                    tax_amount=tax,
                    amount=money(net + tax),
                )
            )


@router.post("/drafts/{draft_id}/transfer", response_model=AssistantDraftOut)
def transfer_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    draft = (
        db.query(QuoteAssistantDraft)
        .filter(QuoteAssistantDraft.id == draft_id)
        .with_for_update()
        .one_or_none()
    )
    if draft is None:
        raise HTTPException(status_code=404, detail="Assistentenentwurf nicht gefunden")
    if draft.quote_id is not None:
        return draft_out(draft)
    if draft.status != AssistantDraftStatus.approved:
        raise _conflict(
            "draft_not_approved",
            "Vor PDF und Übernahme ist eine ausdrückliche Freigabe erforderlich.",
        )

    client, _ = _client_project(db, draft.client_id, draft.project_id)
    company = _get_or_create_settings(db, lock_for_invoice_number=True)
    today = date.today()
    quote = Quote(
        client_id=draft.client_id,
        project_id=draft.project_id,
        quote_number=f"{company.quote_number_prefix}-{today.year}-{company.next_quote_number:04d}",
        issue_date=today,
        valid_until=today + timedelta(days=14),
        status=QuoteStatus.draft,
        notes=draft.notes,
        subtotal=draft.net_total,
        tax_total=draft.tax_total,
        total=draft.total,
    )
    db.add(quote)
    db.flush()
    for line in sorted(draft.lines, key=lambda item: item.sort_order):
        quote.line_items.append(
            QuoteLineItem(
                description=line.description,
                quantity=line.quantity,
                unit=line.unit,
                unit_price=line.unit_price,
                net_amount=line.net_amount,
                tax_rate=line.tax_rate,
                tax_amount=line.tax_amount,
                amount=line.amount,
            )
        )
    preview_result = calculate_preview(
        pricing_date=draft.pricing_date,
        lines=draft_out(draft).lines,
        surcharge_percent=draft.surcharge_percent,
        discount_percent=draft.discount_percent,
    )
    _append_adjustment_lines(quote, draft, preview_result)
    company.next_quote_number += 1
    draft.quote_id = quote.id
    draft.status = AssistantDraftStatus.transferred
    draft.transferred_at = utc_now_naive()
    db.flush()
    db.refresh(quote)

    expected_path = os.path.join(
        app_settings.pdf_storage_dir, f"quote-{quote.quote_number}.pdf"
    )
    try:
        quote.pdf_path = generate_quote_pdf(quote, client, company)
        db.commit()
    except Exception as exc:
        db.rollback()
        try:
            os.remove(expected_path)
        except FileNotFoundError:
            pass
        raise HTTPException(
            status_code=500,
            detail=f"Angebot konnte nicht übernommen werden (PDF-Fehler: {exc})",
        )
    db.refresh(draft)
    return draft_out(draft)
