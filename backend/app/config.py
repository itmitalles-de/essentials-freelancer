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

    pdf_storage_dir: str = "/data/invoices"
    run_migrations: bool = True


settings = Settings()
