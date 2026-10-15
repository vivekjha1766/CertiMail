from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
EXTRACT_DIR = DATA_DIR / "extracted"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXTRACT_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseSettings):
    APP_NAME: str = "CertiMail — Certificate Distribution Dashboard"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    DATABASE_PATH: str = str(DATA_DIR / "certimailer.db")
    
    # SMTP defaults (can be overridden via UI or env)
    SMTP_HOST: Optional[str] = "smtp.gmail.com"
    SMTP_PORT: Optional[int] = 587
    SMTP_USE_TLS: Optional[bool] = True
    SMTP_USE_SSL: Optional[bool] = False
    SMTP_SENDER_NAME: Optional[str] = "CertiMail Admin"
    SMTP_SENDER_EMAIL: Optional[str] = ""
    SMTP_USERNAME: Optional[str] = ""
    SMTP_PASSWORD: Optional[str] = ""
    
    GLOBAL_CC: Optional[str] = ""
    GLOBAL_BCC: Optional[str] = ""
    
    # Max file size limits: 200MB for ZIP archives, 50MB for Excel
    MAX_EXCEL_BYTES: int = 50 * 1024 * 1024
    MAX_ZIP_BYTES: int = 200 * 1024 * 1024
    
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
