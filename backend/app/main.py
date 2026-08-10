from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, SessionLocal, engine
from app.models import CompanySettings, User
from app.routers import auth, clients, invoices, settings as settings_router, time_entries
from app.security import hash_password
from app.config import settings


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
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_admin()
    yield


app = FastAPI(title="itmitalles tracker", lifespan=lifespan)

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
app.include_router(settings_router.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
