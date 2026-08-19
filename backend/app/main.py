from contextlib import asynccontextmanager
import json
import logging
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, SessionLocal, engine, get_db
from app.models import CompanySettings, User
from app.module_registry import SCHEMA_VERSION
from app.module_service import reconcile_module_installations
from app.routers import (
    auth,
    clients,
    expenses,
    invoices,
    modules,
    projects,
    quote_assistant,
    quotes,
    reports,
    settings as settings_router,
    time_entries,
)
from app.security import hash_password

logger = logging.getLogger("freelancer.http")


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


app = FastAPI(
    title="Essentials+ Freelancer",
    version=settings.product_version,
    lifespan=lifespan,
)

allowed_origins = [
    origin.strip()
    for origin in settings.cors_allowed_origins.split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    started = perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
    finally:
        route = request.scope.get("route")
        route_template = getattr(route, "path", "<unmatched>")
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "route": route_template,
                    "status": status_code,
                    "duration_ms": round((perf_counter() - started) * 1000, 2),
                },
                separators=(",", ":"),
            )
        )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), geolocation=(), microphone=()"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


@app.exception_handler(HTTPException)
async def structured_http_error(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        code = str(exc.detail.get("code", f"http_{exc.status_code}"))
        message = str(exc.detail.get("message", "Anfrage konnte nicht verarbeitet werden"))
    else:
        code = f"http_{exc.status_code}"
        message = str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={
            "detail": exc.detail,
            "error": {"code": code, "message": message},
            "request_id": _request_id(request),
        },
    )


@app.exception_handler(RequestValidationError)
async def structured_validation_error(request: Request, exc: RequestValidationError):
    details = [
        {"location": list(error["loc"]), "message": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "detail": details,
            "error": {
                "code": "validation_error",
                "message": "Eingabedaten sind ungültig",
                "details": details,
            },
            "request_id": _request_id(request),
        },
    )

app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(time_entries.router)
app.include_router(invoices.router)
app.include_router(projects.router)
app.include_router(quotes.router)
app.include_router(quote_assistant.router)
app.include_router(expenses.router)
app.include_router(settings_router.router)
app.include_router(modules.router)
app.include_router(reports.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/ready")
def readiness(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        if settings.run_migrations:
            revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
            if revision != SCHEMA_VERSION:
                raise RuntimeError("schema revision mismatch")
        else:
            revision = "metadata"
    except Exception:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "not_ready",
                "message": "Datenbank oder Schema ist nicht bereit",
            },
        )
    return {
        "status": "ready",
        "database": "ready",
        "schema_revision": revision,
        "expected_schema_revision": SCHEMA_VERSION,
    }


@app.get("/api/meta")
def metadata(db: Session = Depends(get_db)):
    ready = readiness(db)
    return {
        "product": "Essentials+ Freelancer",
        "product_version": app.version,
        "schema_revision": ready["schema_revision"],
        "repository_revision": settings.repository_revision,
        "build_time": settings.build_time,
        "readiness": ready["status"],
    }
