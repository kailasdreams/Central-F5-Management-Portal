from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db, SessionLocal
from app import models
from app.auth import hash_password
from app.routers import auth as auth_router
from app.routers import devices as devices_router
from app.routers import cli as cli_router
from app.routers import logs as logs_router
from app.routers import backups as backups_router
from app.routers import audit as audit_router
from app.services import scheduler as scheduler_module

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.APP_NAME, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(devices_router.router)
app.include_router(cli_router.router)
app.include_router(logs_router.router)
app.include_router(backups_router.router)
app.include_router(audit_router.router)


def _seed_default_admin():
    """Creates a default admin/admin123 account on first run only, if no users exist.
    Change this password immediately after first login."""
    db = SessionLocal()
    try:
        if db.query(models.User).count() == 0:
            admin = models.User(
                username="admin",
                password_hash=hash_password("admin123"),
                role="admin",
            )
            db.add(admin)
            db.commit()
            print("[SEED] Default admin user created -> username: admin / password: admin123"
                  " -- CHANGE THIS IMMEDIATELY.")
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    _seed_default_admin()
    scheduler_module.start()


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}
