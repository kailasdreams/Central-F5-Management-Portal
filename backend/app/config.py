"""
Central configuration for F5 Central Management Portal.
All secrets are pulled from environment variables (.env) - never hardcode.
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "F5 Central Management Portal"

    # --- Database ---
    # For docker-compose this is overridden to sqlite:////app/data/f5_portal.db
    # so the DB file lands on the persistent db_data volume.
    DATABASE_URL: str = "sqlite:///./f5_portal.db"

    # --- JWT Auth ---
    JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480  # 8 hour session

    # --- Credential Vault ---
    # Fernet key. Generate once with: from cryptography.fernet import Fernet; Fernet.generate_key()
    VAULT_KEY: str = os.environ.get("VAULT_KEY", "")

    # --- Backup storage ---
    BACKUP_STORAGE_DIR: str = "./backup_storage"

    # --- Remote backup (SCP) target - optional, can be overridden per schedule ---
    DEFAULT_REMOTE_BACKUP_HOST: str = os.environ.get("DEFAULT_REMOTE_BACKUP_HOST", "")
    DEFAULT_REMOTE_BACKUP_USER: str = os.environ.get("DEFAULT_REMOTE_BACKUP_USER", "")
    DEFAULT_REMOTE_BACKUP_PATH: str = os.environ.get("DEFAULT_REMOTE_BACKUP_PATH", "/backups/f5")

    # --- CORS ---
    CORS_ORIGINS: list = ["*"]

    class Config:
        env_file = ".env"


settings = Settings()

os.makedirs(settings.BACKUP_STORAGE_DIR, exist_ok=True)

if settings.DATABASE_URL.startswith("sqlite:///"):
    _db_path = settings.DATABASE_URL.replace("sqlite:///", "", 1)
    _db_dir = os.path.dirname(_db_path)
    if _db_dir:
        os.makedirs(_db_dir, exist_ok=True)
