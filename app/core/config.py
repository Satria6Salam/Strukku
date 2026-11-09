"""Konfigurasi aplikasi.

Semua nilai bisa diubah lewat file `.env` atau environment variable tanpa
menyentuh kode. Path relatif selalu dihitung dari folder utama project
(bukan dari folder tempat terminal dibuka), sehingga server bisa dijalankan
dari mana saja.
"""
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # --- Aplikasi -----------------------------------------------------------
    APP_NAME: str = "STRUKKU Backend API"
    APP_VERSION: str = "2.0.0"
    APP_ENV: str = "development"  # development | production
    API_PREFIX: str = "/api/v1"
    TIMEZONE: str = "Asia/Jakarta"
    CORS_ORIGINS: str = "*"  # pisahkan dengan koma, mis. "https://a.com,https://b.com"

    # --- Database -----------------------------------------------------------
    DATABASE_URL: str = "sqlite:///./strukku.db"
    AUTO_MIGRATE: bool = True  # jalankan migrasi Alembic otomatis saat server start
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT_SECONDS: int = 30
    DB_POOL_RECYCLE_SECONDS: int = 1800

    # --- Autentikasi --------------------------------------------------------
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REQUIRE_EMAIL_VERIFICATION: bool = True
    EMAIL_VERIFICATION_EXPIRE_MINUTES: int = 24 * 60
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30

    # --- Rate limit login ---------------------------------------------------
    LOGIN_RATE_LIMIT: int = 5
    LOGIN_RATE_WINDOW_MINUTES: int = 15
    TRUST_PROXY_HEADERS: bool = False

    # --- Email --------------------------------------------------------------
    PUBLIC_BASE_URL: str = "http://127.0.0.1:8000"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    SMTP_TIMEOUT_SECONDS: int = 10

    # --- Machine Learning ---------------------------------------------------
    MODEL_PATH: str = "models/model_tfidf_mnb_v1.joblib"
    # Urutan penentu kategori. Yang pertama memberi jawaban akan dipakai.
    CLASSIFIER_PIPELINE: str = "user_history,keyword_rules,ml_model"
    KEYWORD_RULES_PATH: str = "app/data/keyword_rules.json"
    CATEGORY_CATALOG_PATH: str = "app/data/category_catalog.json"
    LOW_CONFIDENCE_THRESHOLD: float = 0.7  # di bawah ini item ditandai "Periksa"

    # --- OCR ----------------------------------------------------------------
    OCR_ENGINE: str = "tesseract"
    TESSERACT_CMD: str = ""  # kosong = cari tesseract di PATH
    OCR_LANG: str = "ind+eng"
    OCR_PSM: int = 4

    # --- Penyimpanan gambar -------------------------------------------------
    STORAGE_BACKEND: str = "local"
    UPLOAD_DIR: str = "storage/uploads"
    MAX_UPLOAD_MB: int = 8
    SCAN_ASSET_EXPIRE_HOURS: int = 24
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "receipt-private"
    SUPABASE_SIGNED_URL_EXPIRY_SECONDS: int = 300

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 48:
            raise ValueError("JWT_SECRET_KEY harus memiliki minimal 48 karakter")
        if value.lower().startswith(("dev-secret-", "generate-a-random-", "replace-with-", "test-only-secret")):
            raise ValueError("JWT_SECRET_KEY tidak boleh memakai nilai placeholder bawaan")
        return value

    @model_validator(mode="after")
    def validate_production_database(self):
        if self.APP_ENV.lower() == "production" and self.is_sqlite:
            raise ValueError(
                "APP_ENV=production tidak boleh memakai SQLite. "
                "Gunakan PostgreSQL/Supabase pada DATABASE_URL."
            )
        if self.APP_ENV.lower() == "production" and self.STORAGE_BACKEND.strip().lower() == "local":
            raise ValueError(
                "APP_ENV=production tidak boleh memakai STORAGE_BACKEND=local. "
                "Gunakan object storage seperti Supabase Storage."
            )
        if (
            self.APP_ENV.lower() == "production"
            and self.STORAGE_BACKEND.strip().lower() == "supabase"
            and (not self.SUPABASE_URL.strip() or not self.SUPABASE_SERVICE_ROLE_KEY.strip())
        ):
            raise ValueError(
                "Produksi Supabase Storage memerlukan SUPABASE_URL dan "
                "SUPABASE_SERVICE_ROLE_KEY."
            )
        return self

    # ------------------------------------------------------------------ helper
    def path(self, value: str) -> Path:
        p = Path(value)
        return p if p.is_absolute() else BASE_DIR / p

    @property
    def database_url(self) -> str:
        """URL database; path SQLite relatif diubah menjadi absolut."""
        url = self.DATABASE_URL
        prefix = "sqlite:///"
        if url.startswith(prefix) and not url.startswith("sqlite:////") and ":memory:" not in url:
            raw = url[len(prefix):]
            if not Path(raw).is_absolute():
                return prefix + (BASE_DIR / raw).resolve().as_posix()
        return url

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def classifier_pipeline(self) -> list[str]:
        return [s.strip() for s in self.CLASSIFIER_PIPELINE.split(",") if s.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
