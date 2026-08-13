from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.config import settings


PRODUCT_VERSION = "0.2.0"
SCHEMA_VERSION = "0004_quote_assistant"


class ModuleState(StrEnum):
    not_installed = "not_installed"
    needs_configuration = "needs_configuration"
    disabled = "disabled"
    enabled = "enabled"
    degraded = "degraded"


class ModuleType(StrEnum):
    core = "core"
    built_in = "built_in"
    connector = "connector"
    custom = "custom"


class ConfigurationRequirement(BaseModel):
    key: str
    label: str
    required: bool = True
    source: str = "environment"


class SecretRequirement(BaseModel):
    key: str
    label: str
    required: bool = True
    source: str = "environment"


class ModuleManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    schema_version: int = 1
    display_name: str
    description: str
    group: str
    module_type: ModuleType
    required: bool
    default_state: ModuleState
    dependencies: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    compatible_product_versions: str = ">=0.2,<1.0"
    compatible_schema_versions: str = ">=0003_modules"
    configuration_fields: tuple[ConfigurationRequirement, ...] = ()
    secret_requirements: tuple[SecretRequirement, ...] = ()
    api_boundaries: tuple[str, ...]
    navigation_boundaries: tuple[str, ...] = ()
    job_boundaries: tuple[str, ...] = ()
    healthcheck: str
    data_ownership: tuple[str, ...]
    export_behavior: str
    backup_behavior: str
    restore_behavior: str
    activation_behavior: str
    deactivation_behavior: str
    update_behavior: str


class RequirementStatus(BaseModel):
    key: str
    configured: bool


class ModuleHealth(BaseModel):
    status: str
    message: str


class ModuleStatus(BaseModel):
    manifest: ModuleManifest
    state: ModuleState
    configuration: list[RequirementStatus]
    secrets: list[RequirementStatus]
    health: ModuleHealth


COMMON_EXPORT = "Rows owned by the module are included in the PostgreSQL business-data export."
COMMON_BACKUP = "Database rows and referenced documents are part of the complete backup unit."
COMMON_RESTORE = "Data is restored by the empty-target business-data restore before migrations run."
COMMON_UPDATE = "Additive Alembic migrations preserve existing rows and compatibility identifiers."


def _core(
    *,
    module_id: str,
    name: str,
    description: str,
    group: str,
    dependencies: tuple[str, ...],
    api: tuple[str, ...],
    navigation: tuple[str, ...],
    data: tuple[str, ...],
) -> ModuleManifest:
    return ModuleManifest(
        id=module_id,
        display_name=name,
        description=description,
        group=group,
        module_type=ModuleType.core,
        required=True,
        default_state=ModuleState.enabled,
        dependencies=dependencies,
        api_boundaries=api,
        navigation_boundaries=navigation,
        healthcheck="Authenticated API and database readiness",
        data_ownership=data,
        export_behavior=COMMON_EXPORT,
        backup_behavior=COMMON_BACKUP,
        restore_behavior=COMMON_RESTORE,
        activation_behavior="Seeded enabled and reconciled at application startup.",
        deactivation_behavior="Required core module; deactivation is rejected without changing data.",
        update_behavior=COMMON_UPDATE,
    )


MODULES: tuple[ModuleManifest, ...] = (
    _core(
        module_id="core.platform",
        name="Plattform und Administration",
        description="Single-administrator authentication, company settings, health, and module administration.",
        group="Arbeit",
        dependencies=(),
        api=("/api/auth/me", "/api/settings", "/api/admin/modules"),
        navigation=("/settings", "/admin/modules"),
        data=("users", "company_settings", "module_installations", "module_audit_events"),
    ),
    _core(
        module_id="core.clients",
        name="Kunden",
        description="Customer master data for the single installation.",
        group="Arbeit",
        dependencies=("core.platform",),
        api=("/api/clients",),
        navigation=("/clients",),
        data=("clients",),
    ),
    _core(
        module_id="core.projects",
        name="Projekte",
        description="Customer-bound projects and project-specific hourly rates.",
        group="Arbeit",
        dependencies=("core.clients",),
        api=("/api/projects",),
        navigation=("/projects",),
        data=("projects",),
    ),
    _core(
        module_id="core.time_tracking",
        name="Zeiterfassung",
        description="Manual time records and the single global timer.",
        group="Arbeit",
        dependencies=("core.clients", "core.projects"),
        api=("/api/time-entries",),
        navigation=("/time",),
        data=("time_entries",),
    ),
    ModuleManifest(
        id="sales.quotes",
        display_name="Angebote",
        description="Version-stable quote documents, lifecycle, PDF, and controlled invoice conversion.",
        group="Verkauf und Angebote",
        module_type=ModuleType.built_in,
        required=False,
        default_state=ModuleState.enabled,
        dependencies=("core.clients", "core.projects"),
        api_boundaries=("/api/quotes",),
        navigation_boundaries=("/quotes",),
        healthcheck="Quote database and document storage availability",
        data_ownership=("quotes", "quote_line_items", "quote PDFs"),
        export_behavior=COMMON_EXPORT,
        backup_behavior=COMMON_BACKUP,
        restore_behavior=COMMON_RESTORE,
        activation_behavior="Enables quote APIs and navigation without altering existing quotes.",
        deactivation_behavior="Stops new quote operations; existing quotes and documents remain stored.",
        update_behavior=COMMON_UPDATE,
    ),
    ModuleManifest(
        id="sales.quote_assistant",
        display_name="Angebotsassistent",
        description="Deterministic catalog, package, template, preview, and approval workflow.",
        group="Verkauf und Angebote",
        module_type=ModuleType.built_in,
        required=False,
        default_state=ModuleState.disabled,
        dependencies=("sales.quotes",),
        api_boundaries=("/api/quote-assistant",),
        navigation_boundaries=("/quote-assistant",),
        healthcheck="Assistant schema and dependency availability",
        data_ownership=(
            "quote_catalog_items",
            "quote_catalog_versions",
            "quote_packages",
            "quote_package_versions",
            "quote_assistant_templates",
            "quote_assistant_drafts",
        ),
        export_behavior=COMMON_EXPORT,
        backup_behavior=COMMON_BACKUP,
        restore_behavior=COMMON_RESTORE,
        activation_behavior="Enables deterministic draft creation; no draft is automatically approved.",
        deactivation_behavior="Stops assistant APIs and navigation without deleting catalogs, versions, or drafts.",
        update_behavior=COMMON_UPDATE,
    ),
    _core(
        module_id="billing.invoices",
        name="Rechnungen",
        description="Invoices from time or accepted quotes, controlled status, PDF, and payment marking.",
        group="Abrechnung",
        dependencies=("core.clients", "core.time_tracking"),
        api=("/api/invoices",),
        navigation=("/invoices",),
        data=("invoices", "invoice_line_items", "invoice PDFs"),
    ),
    ModuleManifest(
        id="expenses.receipts",
        display_name="Ausgaben und Belege",
        description="Expense records with validated PNG, JPEG, or PDF receipts.",
        group="Ausgaben",
        module_type=ModuleType.built_in,
        required=False,
        default_state=ModuleState.enabled,
        dependencies=("core.platform",),
        api_boundaries=("/api/expenses",),
        navigation_boundaries=("/expenses",),
        healthcheck="Expense schema and document storage availability",
        data_ownership=("expenses", "receipt documents"),
        export_behavior=COMMON_EXPORT,
        backup_behavior=COMMON_BACKUP,
        restore_behavior=COMMON_RESTORE,
        activation_behavior="Enables expense and receipt operations.",
        deactivation_behavior="Stops new expense operations; rows and receipts remain stored.",
        update_behavior=COMMON_UPDATE,
    ),
    ModuleManifest(
        id="communication.smtp",
        display_name="E-Mail-Versand",
        description="SMTP delivery of generated invoice PDFs.",
        group="Kommunikation",
        module_type=ModuleType.connector,
        required=False,
        default_state=ModuleState.enabled,
        dependencies=("billing.invoices",),
        configuration_fields=(
            ConfigurationRequirement(key="smtp_host", label="SMTP host"),
            ConfigurationRequirement(key="smtp_port", label="SMTP port"),
            ConfigurationRequirement(key="smtp_from", label="Sender address"),
        ),
        secret_requirements=(
            SecretRequirement(
                key="smtp_password",
                label="SMTP password when authenticated SMTP is used",
                required=False,
            ),
        ),
        api_boundaries=("POST /api/invoices/{id}/send",),
        navigation_boundaries=(),
        healthcheck="Required SMTP configuration is present; delivery is verified only by an explicit send.",
        data_ownership=(),
        export_behavior="No connector secret or SMTP message is included in business-data exports.",
        backup_behavior="No connector secret is stored in application backups.",
        restore_behavior="Host-managed SMTP configuration must be supplied separately after restore.",
        activation_behavior="Enables send operations when required non-secret configuration is present.",
        deactivation_behavior="Stops new send operations; invoice states and PDFs remain unchanged.",
        update_behavior="Configuration contract changes require an explicit manifest schema update.",
    ),
    ModuleManifest(
        id="core.reporting",
        display_name="Operative Auswertung",
        description="Filtered operational summaries and CSV exports without tax or legal interpretation.",
        group="Export und Integrationen",
        module_type=ModuleType.built_in,
        required=False,
        default_state=ModuleState.enabled,
        dependencies=("core.time_tracking", "billing.invoices"),
        api_boundaries=("/api/reports",),
        navigation_boundaries=("/",),
        healthcheck="Reporting queries can access the current schema.",
        data_ownership=(),
        export_behavior="Produces filtered CSV views; it does not create additional authoritative rows.",
        backup_behavior="No additional state beyond source business tables.",
        restore_behavior="Reports are recomputed from restored business tables.",
        activation_behavior="Enables reporting API, dashboard cards, filters, and CSV downloads.",
        deactivation_behavior="Stops report generation; source business data remains unchanged.",
        update_behavior=COMMON_UPDATE,
    ),
    ModuleManifest(
        id="export.business_data",
        display_name="Geschäftsdaten-Export",
        description="Consistent PostgreSQL and document-volume export with checksum and revision manifest.",
        group="Export und Integrationen",
        module_type=ModuleType.built_in,
        required=False,
        default_state=ModuleState.enabled,
        dependencies=("core.platform",),
        api_boundaries=("scripts/export-business-data.sh",),
        navigation_boundaries=(),
        job_boundaries=("explicit host-side export invocation",),
        healthcheck="Checked by the reproducible export and empty-target restore rehearsal.",
        data_ownership=("export manifests",),
        export_behavior="Creates the complete business-data export.",
        backup_behavior="Export artifacts are backup inputs but remain outside the application database.",
        restore_behavior="Restore refuses non-empty targets and checksum mismatches.",
        activation_behavior="Allows host-side export jobs to be trusted only after a successful rehearsal.",
        deactivation_behavior="Stops scheduled module-aware export jobs; it never deletes existing exports.",
        update_behavior="Manifest format changes remain backward-readable or require a documented migration.",
    ),
    ModuleManifest(
        id="backup.offsite",
        display_name="Verschlüsseltes Offsite-Backup",
        description="Host-managed encrypted restic snapshots of complete business-data exports.",
        group="Export und Integrationen",
        module_type=ModuleType.connector,
        required=False,
        default_state=ModuleState.disabled,
        dependencies=("export.business_data",),
        configuration_fields=(
            ConfigurationRequirement(
                key="offsite_repository_configured",
                label="Restic repository configured on host",
            ),
        ),
        secret_requirements=(
            SecretRequirement(
                key="offsite_password_file_configured",
                label="Protected restic password file configured on host",
            ),
        ),
        api_boundaries=("scripts/offsite-backup.sh",),
        navigation_boundaries=(),
        job_boundaries=("freelancer-backup.service", "freelancer-backup.timer"),
        healthcheck="Host readiness indicators only; a real provider requires external restore evidence.",
        data_ownership=("encrypted restic snapshots outside application storage",),
        export_behavior="Consumes complete local business-data exports.",
        backup_behavior="Encrypts exports in the configured restic repository and applies retention.",
        restore_behavior="Requires an explicit restic restore followed by the empty-target application restore.",
        activation_behavior="Marks the connector available only when host readiness indicators are present.",
        deactivation_behavior="Module-aware schedules stop creating snapshots; existing snapshots are retained.",
        update_behavior="Provider configuration remains host-managed and outside Git.",
    ),
)

MODULE_BY_ID = {module.id: module for module in MODULES}


def _configured_value(key: str) -> bool:
    value = getattr(settings, key, None)
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value > 0
    return bool(value)


def requirement_statuses(
    requirements: tuple[ConfigurationRequirement | SecretRequirement, ...],
) -> list[RequirementStatus]:
    return [
        RequirementStatus(key=requirement.key, configured=_configured_value(requirement.key))
        for requirement in requirements
    ]


def missing_required_configuration(manifest: ModuleManifest) -> list[str]:
    missing = []
    for requirement in (*manifest.configuration_fields, *manifest.secret_requirements):
        if requirement.required and not _configured_value(requirement.key):
            missing.append(requirement.key)
    return missing


HealthCheck = Callable[[], ModuleHealth]


def configured_health(manifest: ModuleManifest) -> ModuleHealth:
    missing = missing_required_configuration(manifest)
    if missing:
        return ModuleHealth(
            status="needs_configuration",
            message="Required configuration is missing: " + ", ".join(missing),
        )
    return ModuleHealth(status="healthy", message="Automated module checks passed.")
