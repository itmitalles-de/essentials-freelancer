from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, SessionLocal, engine, get_db
from app.models import CompanySettings, User
from app.module_service import reconcile_module_installations
from app.routers import (
    auth,
    clients,
    expenses,
    invoices,
    modules,
    projects,
    quotes,
    settings as settings_router,
    time_entries,
)
from app.security import hash_password


def seed_admin() -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == settings.admin_username).first() is None:
            db.add(
                User(
                    username=settings.admin_username,
                    password_hash=hash_password(settings.admin_password),
                )
            )
        if db.get(CompanySettings, 1) is None:
            db.add(CompanySettings(id=1))
        db.commit()
        reconcile_module_installations(db)
    finally:
        db.close()


def migrate_database() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(backend_dir / "alembic.ini")
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(config, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.run_migrations:
        migrate_database()
    else:
        Base.metadata.create_all(bind=engine)
    seed_admin()
    yield


app = FastAPI(title="Essentials+ Freelancer", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(time_entries.router)
app.include_router(invoices.router)
app.include_router(projects.router)
app.include_router(quotes.router)
app.include_router(expenses.router)
app.include_router(settings_router.router)
app.include_router(modules.router)


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
