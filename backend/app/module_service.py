from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import ModuleAuditEvent, ModuleInstallation
from app.module_registry import (
    MODULES,
    MODULE_BY_ID,
    PILOT_LOCKED_MODULES,
    ModuleHealth,
    ModuleManifest,
    ModuleState,
    ModuleStatus,
    configured_health,
    missing_required_configuration,
    requirement_statuses,
)
from app.time_utils import utc_now_naive


ACTIVE_STATES = {
    ModuleState.enabled,
    ModuleState.needs_configuration,
    ModuleState.degraded,
}


def _initial_state(manifest: ModuleManifest) -> ModuleState:
    if manifest.required:
        return ModuleState.enabled
    return manifest.default_state


def reconcile_module_installations(db: Session) -> None:
    changed = False
    for manifest in MODULES:
        installation = db.get(ModuleInstallation, manifest.id)
        if installation is None:
            installation = ModuleInstallation(
                module_id=manifest.id,
                manifest_schema_version=manifest.schema_version,
                state=_initial_state(manifest).value,
            )
            db.add(installation)
            db.flush()
            changed = True
        elif installation.manifest_schema_version != manifest.schema_version:
            installation.manifest_schema_version = manifest.schema_version
            installation.updated_at = utc_now_naive()
            changed = True

        current = ModuleState(installation.state)
        if manifest.id in PILOT_LOCKED_MODULES and current != ModuleState.disabled:
            installation.state = ModuleState.disabled.value
            installation.updated_at = utc_now_naive()
            changed = True
        elif manifest.required and current != ModuleState.enabled:
            installation.state = ModuleState.enabled.value
            installation.updated_at = utc_now_naive()
            changed = True
        elif current in {
            ModuleState.enabled,
            ModuleState.needs_configuration,
            ModuleState.degraded,
        }:
            evaluated = _evaluate_enabled_state(manifest)
            if evaluated != current:
                installation.state = evaluated.value
                installation.updated_at = utc_now_naive()
                changed = True
    if changed:
        db.commit()


def _manifest_or_404(module_id: str) -> ModuleManifest:
    manifest = MODULE_BY_ID.get(module_id)
    if manifest is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "module_not_found",
                "message": "Das Modul ist nicht im Produktkatalog enthalten.",
                "module_id": module_id,
            },
        )
    return manifest


def _installation(db: Session, module_id: str, *, lock: bool = False) -> ModuleInstallation:
    query = db.query(ModuleInstallation).filter(ModuleInstallation.module_id == module_id)
    if lock:
        query = query.with_for_update()
    installation = query.one_or_none()
    if installation is None:
        reconcile_module_installations(db)
        installation = db.get(ModuleInstallation, module_id)
    if installation is None:
        raise RuntimeError(f"module installation was not seeded: {module_id}")
    return installation


def _evaluate_enabled_state(manifest: ModuleManifest) -> ModuleState:
    if missing_required_configuration(manifest):
        return ModuleState.needs_configuration
    try:
        health = configured_health(manifest)
    except Exception:
        return ModuleState.degraded
    return ModuleState.enabled if health.status == "healthy" else ModuleState.degraded


def module_status(db: Session, module_id: str) -> ModuleStatus:
    manifest = _manifest_or_404(module_id)
    installation = _installation(db, module_id)
    state = ModuleState(installation.state)
    if state == ModuleState.disabled:
        health = ModuleHealth(status="disabled", message="Das Modul ist deaktiviert.")
    elif state == ModuleState.not_installed:
        health = ModuleHealth(
            status="not_installed", message="Das Modul ist nicht installiert."
        )
    else:
        evaluated = _evaluate_enabled_state(manifest)
        if evaluated != state:
            installation.state = evaluated.value
            installation.updated_at = utc_now_naive()
            db.commit()
            state = evaluated
        health = configured_health(manifest)
        if state == ModuleState.degraded:
            health = ModuleHealth(
                status="degraded", message="Der automatisierte Healthcheck ist fehlgeschlagen."
            )
    return ModuleStatus(
        manifest=manifest,
        state=state,
        configuration=requirement_statuses(manifest.configuration_fields),
        secrets=requirement_statuses(manifest.secret_requirements),
        health=health,
    )


def list_module_statuses(db: Session) -> list[ModuleStatus]:
    reconcile_module_installations(db)
    return [module_status(db, manifest.id) for manifest in MODULES]


def ensure_module_available(db: Session, module_id: str) -> ModuleInstallation:
    if module_id in PILOT_LOCKED_MODULES:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "pilot_module_locked",
                "message": (
                    "SMTP ist für den internen Pilot deaktiviert. "
                    "Rechnungs-PDF manuell herunterladen und versenden."
                ),
                "module_id": module_id,
                "state": ModuleState.disabled.value,
            },
        )
    status = module_status(db, module_id)
    if status.state != ModuleState.enabled:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "module_unavailable",
                "message": f"Modul {module_id} ist nicht verfügbar ({status.state.value}).",
                "module_id": module_id,
                "state": status.state.value,
            },
        )
    return _installation(db, module_id)


def _audit(
    db: Session,
    *,
    installation: ModuleInstallation,
    action: str,
    previous_state: ModuleState,
    actor: str,
) -> None:
    db.add(
        ModuleAuditEvent(
            module_id=installation.module_id,
            action=action,
            previous_state=previous_state.value,
            resulting_state=installation.state,
            actor=actor,
        )
    )


def enable_module(db: Session, module_id: str, actor: str) -> ModuleStatus:
    manifest = _manifest_or_404(module_id)
    if module_id in PILOT_LOCKED_MODULES:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "pilot_module_locked",
                "message": (
                    "SMTP bleibt deaktiviert, bis der crash-sichere Versandvertrag "
                    "vollständig implementiert und getestet ist."
                ),
                "module_id": module_id,
            },
        )
    installation = _installation(db, module_id, lock=True)
    previous = ModuleState(installation.state)

    for dependency_id in manifest.dependencies:
        dependency = module_status(db, dependency_id)
        if dependency.state != ModuleState.enabled:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "module_dependency_unavailable",
                    "message": f"Abhängigkeit {dependency_id} ist nicht aktiviert und gesund.",
                    "module_id": module_id,
                    "dependency_id": dependency_id,
                },
            )
    for conflict_id in manifest.conflicts:
        conflict = module_status(db, conflict_id)
        if conflict.state in ACTIVE_STATES:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "module_conflict",
                    "message": f"Konfliktmodul {conflict_id} ist aktiv.",
                    "module_id": module_id,
                    "conflict_id": conflict_id,
                },
            )

    target = _evaluate_enabled_state(manifest)
    installation.state = target.value
    installation.updated_at = utc_now_naive()
    action = "enable_noop" if previous == target else "enable"
    _audit(
        db,
        installation=installation,
        action=action,
        previous_state=previous,
        actor=actor,
    )
    db.commit()
    return module_status(db, module_id)


def disable_module(db: Session, module_id: str, actor: str) -> ModuleStatus:
    manifest = _manifest_or_404(module_id)
    installation = _installation(db, module_id, lock=True)
    previous = ModuleState(installation.state)
    if manifest.required:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "required_module",
                "message": "Ein erforderliches Kernmodul kann nicht deaktiviert werden.",
                "module_id": module_id,
            },
        )

    dependents = []
    for dependent_manifest in MODULES:
        if module_id not in dependent_manifest.dependencies:
            continue
        dependent = _installation(db, dependent_manifest.id)
        if ModuleState(dependent.state) in ACTIVE_STATES:
            dependents.append(dependent_manifest.id)
    if dependents:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "module_has_active_dependents",
                "message": "Aktive abhängige Module müssen zuerst deaktiviert werden.",
                "module_id": module_id,
                "dependents": dependents,
            },
        )

    installation.state = ModuleState.disabled.value
    installation.updated_at = utc_now_naive()
    action = "disable_noop" if previous == ModuleState.disabled else "disable"
    _audit(
        db,
        installation=installation,
        action=action,
        previous_state=previous,
        actor=actor,
    )
    db.commit()
    return module_status(db, module_id)
