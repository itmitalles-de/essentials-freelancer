from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import (
    QuoteAssistantDraft,
    QuoteAssistantTemplate,
    QuoteAssistantTemplateVersion,
    QuoteCatalogItem,
    QuoteCatalogVersion,
    QuotePackage,
    QuotePackageVersion,
)
from app.money import PERCENT, as_decimal, line_amounts, money
from app.schemas import (
    AssistantDraftOut,
    AssistantLineOut,
    AssistantPreviewOut,
    AssistantPreviewRequest,
    AssistantSelection,
    CalculationStepOut,
    PackageItemOut,
    PackageOut,
    PackageVersionOut,
    TaxBreakdownOut,
    TemplateOut,
    TemplateVersionOut,
)


def _unavailable(code: str, message: str, **details) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail={"code": code, "message": message, **details},
    )


def _valid_on(valid_from: date, valid_until: date | None, pricing_date: date) -> bool:
    return valid_from <= pricing_date and (
        valid_until is None or pricing_date <= valid_until
    )


def _catalog_version(
    db: Session, version_id: int, pricing_date: date
) -> QuoteCatalogVersion:
    version = db.get(QuoteCatalogVersion, version_id)
    if version is None:
        raise _unavailable(
            "catalog_version_not_found",
            "Die ausgewählte Katalogversion wurde nicht gefunden.",
            catalog_version_id=version_id,
        )
    item = db.get(QuoteCatalogItem, version.item_id)
    if item is None or not item.active:
        raise _unavailable(
            "catalog_item_inactive",
            "Die ausgewählte Katalogposition ist nicht aktiv.",
            catalog_version_id=version_id,
        )
    if not _valid_on(version.valid_from, version.valid_until, pricing_date):
        raise _unavailable(
            "catalog_price_expired",
            "Der Katalogpreis ist am Kalkulationsdatum nicht gültig.",
            catalog_version_id=version_id,
            pricing_date=pricing_date.isoformat(),
        )
    return version


def _package_version(
    db: Session, version_id: int, pricing_date: date
) -> QuotePackageVersion:
    version = db.get(QuotePackageVersion, version_id)
    if version is None:
        raise _unavailable(
            "package_version_not_found",
            "Die ausgewählte Paketversion wurde nicht gefunden.",
            package_version_id=version_id,
        )
    package = db.get(QuotePackage, version.package_id)
    if package is None or not package.active:
        raise _unavailable(
            "package_inactive",
            "Das ausgewählte Leistungspaket ist nicht aktiv.",
            package_version_id=version_id,
        )
    if not _valid_on(version.valid_from, version.valid_until, pricing_date):
        raise _unavailable(
            "package_version_expired",
            "Die Paketversion ist am Kalkulationsdatum nicht gültig.",
            package_version_id=version_id,
            pricing_date=pricing_date.isoformat(),
        )
    return version


def _line(
    *,
    version: QuoteCatalogVersion,
    quantity: Decimal,
    package_version_id: int | None,
    sort_order: int,
) -> AssistantLineOut:
    net, tax, gross = line_amounts(
        quantity, version.net_unit_price, version.tax_rate
    )
    return AssistantLineOut(
        catalog_version_id=version.id,
        package_version_id=package_version_id,
        description=version.description,
        quantity=quantity,
        unit=version.unit,
        unit_price=version.net_unit_price,
        tax_rate=version.tax_rate,
        net_amount=net,
        tax_amount=tax,
        amount=gross,
        sort_order=sort_order,
    )


def _expand_selections(
    db: Session,
    selections: list[AssistantSelection],
    pricing_date: date,
) -> list[AssistantLineOut]:
    lines: list[AssistantLineOut] = []
    for selection in selections:
        if selection.catalog_version_id is not None:
            version = _catalog_version(db, selection.catalog_version_id, pricing_date)
            lines.append(
                _line(
                    version=version,
                    quantity=selection.quantity,
                    package_version_id=None,
                    sort_order=len(lines),
                )
            )
            continue

        package_version = _package_version(
            db, selection.package_version_id or 0, pricing_date
        )
        for item in sorted(package_version.items, key=lambda entry: entry.sort_order):
            catalog_version = _catalog_version(
                db, item.catalog_version_id, pricing_date
            )
            lines.append(
                _line(
                    version=catalog_version,
                    quantity=as_decimal(item.quantity) * selection.quantity,
                    package_version_id=package_version.id,
                    sort_order=len(lines),
                )
            )
    return lines


def calculate_preview(
    *,
    pricing_date: date,
    lines: list[AssistantLineOut],
    surcharge_percent: Decimal,
    discount_percent: Decimal,
) -> AssistantPreviewOut:
    by_tax_rate: dict[Decimal, Decimal] = defaultdict(lambda: Decimal("0"))
    for line in lines:
        by_tax_rate[as_decimal(line.tax_rate)] += as_decimal(line.net_amount)

    breakdown: list[TaxBreakdownOut] = []
    for tax_rate in sorted(by_tax_rate):
        base = money(by_tax_rate[tax_rate])
        surcharge = money(base * surcharge_percent / PERCENT)
        after_surcharge = money(base + surcharge)
        discount = money(after_surcharge * discount_percent / PERCENT)
        taxable = money(after_surcharge - discount)
        tax = money(taxable * tax_rate / PERCENT)
        breakdown.append(
            TaxBreakdownOut(
                tax_rate=tax_rate,
                base_net=base,
                surcharge=surcharge,
                discount=discount,
                taxable_net=taxable,
                tax_amount=tax,
                gross=money(taxable + tax),
            )
        )

    base_net_total = money(sum((item.base_net for item in breakdown), Decimal("0")))
    surcharge_amount = money(
        sum((item.surcharge for item in breakdown), Decimal("0"))
    )
    discount_amount = money(sum((item.discount for item in breakdown), Decimal("0")))
    net_total = money(sum((item.taxable_net for item in breakdown), Decimal("0")))
    tax_total = money(sum((item.tax_amount for item in breakdown), Decimal("0")))
    total = money(net_total + tax_total)

    steps = [
        CalculationStepOut(
            key="base_net",
            label="Positionen netto",
            expression="Summe aus Menge × Nettopreis",
            amount=base_net_total,
        ),
        CalculationStepOut(
            key="surcharge",
            label="Aufschlag",
            expression=f"Positionen netto × {surcharge_percent}%",
            amount=surcharge_amount,
        ),
        CalculationStepOut(
            key="discount",
            label="Rabatt",
            expression=f"(Positionen + Aufschlag) × {discount_percent}%",
            amount=-discount_amount,
        ),
        CalculationStepOut(
            key="net_total",
            label="Angebot netto",
            expression="Positionen + Aufschlag − Rabatt",
            amount=net_total,
        ),
    ]
    for item in breakdown:
        steps.append(
            CalculationStepOut(
                key=f"tax_{item.tax_rate}",
                label=f"Steuer {item.tax_rate}%",
                expression=f"{item.taxable_net} × {item.tax_rate}%",
                amount=item.tax_amount,
            )
        )
    steps.append(
        CalculationStepOut(
            key="gross_total",
            label="Gesamtbetrag",
            expression="Netto + Steuer",
            amount=total,
        )
    )

    return AssistantPreviewOut(
        pricing_date=pricing_date,
        lines=lines,
        tax_breakdown=breakdown,
        calculation_steps=steps,
        base_net_total=base_net_total,
        surcharge_percent=surcharge_percent,
        surcharge_amount=surcharge_amount,
        discount_percent=discount_percent,
        discount_amount=discount_amount,
        net_total=net_total,
        tax_total=tax_total,
        total=total,
    )


def build_preview(db: Session, payload: AssistantPreviewRequest) -> AssistantPreviewOut:
    lines = _expand_selections(db, payload.selections, payload.pricing_date)
    return calculate_preview(
        pricing_date=payload.pricing_date,
        lines=lines,
        surcharge_percent=payload.surcharge_percent,
        discount_percent=payload.discount_percent,
    )


def draft_out(draft: QuoteAssistantDraft) -> AssistantDraftOut:
    lines = [
        AssistantLineOut(
            catalog_version_id=line.catalog_version_id,
            package_version_id=line.package_version_id,
            description=line.description,
            quantity=line.quantity,
            unit=line.unit,
            unit_price=line.unit_price,
            tax_rate=line.tax_rate,
            net_amount=line.net_amount,
            tax_amount=line.tax_amount,
            amount=line.amount,
            sort_order=line.sort_order,
        )
        for line in sorted(draft.lines, key=lambda entry: entry.sort_order)
    ]
    preview = calculate_preview(
        pricing_date=draft.pricing_date,
        lines=lines,
        surcharge_percent=draft.surcharge_percent,
        discount_percent=draft.discount_percent,
    )
    return AssistantDraftOut(
        **preview.model_dump(),
        id=draft.id,
        client_id=draft.client_id,
        project_id=draft.project_id,
        template_version_id=draft.template_version_id,
        quote_id=draft.quote_id,
        title=draft.title,
        status=draft.status,
        guided_answers=json.loads(draft.guided_answers_json or "{}"),
        notes=draft.notes,
        approved_at=draft.approved_at,
        transferred_at=draft.transferred_at,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
    )


def package_out(package: QuotePackage) -> PackageOut:
    versions = []
    for version in sorted(package.versions, key=lambda item: item.version):
        versions.append(
            PackageVersionOut(
                id=version.id,
                package_id=version.package_id,
                version=version.version,
                description=version.description,
                valid_from=version.valid_from,
                valid_until=version.valid_until,
                items=[
                    PackageItemOut(
                        catalog_version_id=item.catalog_version_id,
                        quantity=item.quantity,
                        sort_order=item.sort_order,
                    )
                    for item in sorted(version.items, key=lambda entry: entry.sort_order)
                ],
                created_at=version.created_at,
            )
        )
    return PackageOut(
        id=package.id,
        stable_key=package.stable_key,
        name=package.name,
        active=package.active,
        versions=versions,
        created_at=package.created_at,
    )


def template_out(template: QuoteAssistantTemplate) -> TemplateOut:
    versions = []
    for version in sorted(template.versions, key=lambda item: item.version):
        versions.append(
            TemplateVersionOut(
                id=version.id,
                template_id=version.template_id,
                version=version.version,
                description=version.description,
                questions=json.loads(version.questions_json or "[]"),
                selections=[
                    AssistantSelection(
                        catalog_version_id=item.catalog_version_id,
                        package_version_id=item.package_version_id,
                        quantity=item.quantity,
                    )
                    for item in sorted(
                        version.selections, key=lambda entry: entry.sort_order
                    )
                ],
                surcharge_percent=version.surcharge_percent,
                discount_percent=version.discount_percent,
                created_at=version.created_at,
            )
        )
    return TemplateOut(
        id=template.id,
        stable_key=template.stable_key,
        name=template.name,
        active=template.active,
        versions=versions,
        created_at=template.created_at,
    )
