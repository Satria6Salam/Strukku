import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_jwt_secret_requires_minimum_length():
    with pytest.raises(ValidationError, match="minimal 48 karakter"):
        Settings(
            _env_file=None,
            JWT_SECRET_KEY="short-secret",
            APP_ENV="development",
        )


def test_jwt_secret_rejects_placeholder():
    with pytest.raises(ValidationError, match="placeholder bawaan"):
        Settings(
            _env_file=None,
            JWT_SECRET_KEY="dev-secret-GANTI-di-.env-dengan-string-acak-panjang",
            APP_ENV="development",
        )


def test_jwt_secret_accepts_random_secret():
    secret = "v9F3Lm8Qw2Xk7Pz1Ry6Hs4Cd0Nb5Jt8Ua3Ei7Go2Df4Ml9Qr7Yc"
    settings = Settings(
        _env_file=None,
        JWT_SECRET_KEY=secret,
        APP_ENV="production",
        STORAGE_BACKEND="supabase",
        SUPABASE_URL="https://project.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY="private-service-role-key-for-validation",
        DATABASE_URL="postgresql+psycopg://postgres:password@localhost:5432/strukku?sslmode=require",
    )
    assert settings.JWT_SECRET_KEY == secret


def test_production_rejects_sqlite():
    secret = "v9F3Lm8Qw2Xk7Pz1Ry6Hs4Cd0Nb5Jt8Ua3Ei7Go2Df4Ml9Qr7Yc"
    with pytest.raises(ValidationError, match="APP_ENV=production tidak boleh memakai SQLite"):
        Settings(
            _env_file=None,
            JWT_SECRET_KEY=secret,
            APP_ENV="production",
            DATABASE_URL="sqlite:///./strukku.db",
        )


def test_testing_allows_sqlite():
    secret = "testing-secret-1234567890-abcdefghijklmnopqrstuvwxyz-0123456789"
    settings = Settings(
        _env_file=None,
        JWT_SECRET_KEY=secret,
        APP_ENV="testing",
        DATABASE_URL="sqlite:///:memory:",
    )
    assert settings.is_sqlite is True


def test_production_rejects_local_object_storage():
    secret = "v9F3Lm8Qw2Xk7Pz1Ry6Hs4Cd0Nb5Jt8Ua3Ei7Go2Df4Ml9Qr7Yc"
    with pytest.raises(ValidationError, match="tidak boleh memakai STORAGE_BACKEND=local"):
        Settings(
            _env_file=None,
            JWT_SECRET_KEY=secret,
            APP_ENV="production",
            DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/strukku",
            STORAGE_BACKEND="local",
        )
