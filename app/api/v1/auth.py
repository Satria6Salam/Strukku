from typing import Annotated

from fastapi import APIRouter, Depends, Request, status, Query
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import DB, CurrentUser
from app.core.config import settings
from app.core.password_policy import password_strength
from app.schemas.common import MessageOut
from app.schemas.user import (
    LoginRequest,
    PasswordChange,
    RegisterOut,
    RegisterRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordStrengthRequest,
    PasswordStrengthOut,
    ResendVerificationRequest,
    RefreshTokenRequest,
    RefreshTokenOut,
    SecurityEventOut,
    TokenOut,
    UserOut,
    UserUpdate,
)
from app.services import auth_service

router = APIRouter(tags=["Auth & Profil"])


@router.post("/auth/password-strength", response_model=PasswordStrengthOut)
def password_strength_check(data: PasswordStrengthRequest):
    """Nilai kekuatan password untuk ditampilkan oleh frontend."""
    return PasswordStrengthOut(**password_strength(data.password))


@router.post("/auth/register", response_model=TokenOut | RegisterOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: DB):
    """Buat akun baru dan kirim tautan verifikasi bila kebijakan aktif."""
    return auth_service.register(db, data)


@router.post("/auth/login", response_model=TokenOut)
def login(data: LoginRequest, db: DB, request: Request):
    """Login dengan JSON `{email, password}`. Dipakai aplikasi Flutter."""
    return auth_service.authenticate(
        db,
        data.email,
        data.password,
        _client_ip(request),
        request.headers.get("user-agent"),
    )


@router.post("/auth/token", response_model=TokenOut, include_in_schema=True, summary="Login (form, untuk Swagger)")
def login_form(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DB, request: Request):
    """Dipakai tombol **Authorize** di /docs. Isi *username* dengan email."""
    return auth_service.authenticate(
        db,
        form.username,
        form.password,
        _client_ip(request),
        request.headers.get("user-agent"),
    )


@router.post("/auth/refresh", response_model=TokenOut)
def refresh_token(data: RefreshTokenRequest, db: DB, request: Request):
    return auth_service.refresh_access_token(
        db,
        data.refresh_token,
        _client_ip(request),
        request.headers.get("user-agent"),
    )


@router.post("/auth/logout", response_model=MessageOut)
def logout(data: RefreshTokenRequest, user: CurrentUser, db: DB, request: Request):
    auth_service.logout(
        db,
        user,
        data.refresh_token,
        _client_ip(request),
        request.headers.get("user-agent"),
    )
    return MessageOut(message="Sesi berhasil logout dan refresh token dicabut.")


@router.get("/auth/sessions", response_model=list[RefreshTokenOut])
def active_sessions(user: CurrentUser, db: DB):
    return auth_service.list_active_refresh_tokens(db, user.id)


def _client_ip(request: Request) -> str:
    if settings.TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/auth/verify-email", response_model=MessageOut)
def verify_email(db: DB, token: str = Query(..., min_length=10)):
    auth_service.verify_email(db, token)
    return MessageOut(message="Email berhasil diverifikasi. Silakan login kembali.")


@router.post("/auth/resend-verification", response_model=MessageOut)
def resend_verification(data: ResendVerificationRequest, db: DB):
    auth_service.resend_verification(db, data.email)
    return MessageOut(message="Jika akun membutuhkan verifikasi, tautan baru telah diproses.")


@router.post("/auth/forgot-password", response_model=MessageOut)
def forgot_password(data: PasswordResetRequest, db: DB):
    auth_service.request_password_reset(db, data.email)
    return MessageOut(
        message="Jika email terdaftar, tautan reset password telah dikirim atau diproses."
    )


@router.post("/auth/reset-password", response_model=MessageOut)
def reset_password(data: PasswordResetConfirm, db: DB, request: Request):
    auth_service.reset_password(
        db,
        data,
        _client_ip(request),
        request.headers.get("user-agent"),
    )
    return MessageOut(message="Password berhasil direset. Silakan login dengan password baru.")


@router.get("/auth/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.patch("/users/me", response_model=UserOut)
def update_me(data: UserUpdate, user: CurrentUser, db: DB, request: Request):
    return auth_service.update_profile(
        db,
        user,
        data,
        _client_ip(request),
        request.headers.get("user-agent"),
    )


@router.post("/users/me/password", response_model=MessageOut)
def change_password(data: PasswordChange, user: CurrentUser, db: DB, request: Request):
    auth_service.change_password(
        db,
        user,
        data,
        _client_ip(request),
        request.headers.get("user-agent"),
    )
    return MessageOut(message="Password berhasil diubah.")


@router.get("/auth/security-events", response_model=list[SecurityEventOut])
def security_events(user: CurrentUser, db: DB, limit: int = Query(default=50, ge=1, le=100)):
    """Riwayat aktivitas keamanan untuk akun yang sedang login."""
    from app.services.security_event_service import list_security_events

    return list_security_events(db, user.id, limit)
