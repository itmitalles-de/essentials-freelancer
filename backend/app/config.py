from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://tracker:tracker@db:5432/tracker"
    jwt_secret: str
    jwt_expire_minutes: int = 60 * 24 * 7

    admin_username: str = "admin"
    admin_password: str

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_use_tls: bool = True
    smtp_timeout_seconds: float = 10.0
    login_rate_limit_per_minute: int = 10
    smtp_rate_limit_per_minute: int = 10

    # Comma-separated browser origins. Empty keeps the default same-origin
    # deployment closed while native clients remain unaffected.
    cors_allowed_origins: str = ""
    repository_revision: str = "unknown"

    # The backend only needs readiness indicators for the host-managed restic
    # configuration. Repository locations and password material stay outside
    # the application and are never exposed through the API.
    offsite_repository_configured: bool = False
    offsite_password_file_configured: bool = False

    pdf_storage_dir: str = "/data/invoices"
    run_migrations: bool = True


settings = Settings()
