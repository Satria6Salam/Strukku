from datetime import datetime, timedelta
import hashlib
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, UnauthorizedError
from app.core.security import (
    create_access_token,
    decode_email_verification_token,
    hash_password,
    verify_password,
)
from app.core.rate_limit import login_rate_limiter
from app.core.password_policy import validate_password
from app.core.timeutils import utcnow
from app.models import PasswordResetToken, RefreshToken, User
from app.schemas.user import (
    PasswordChange,
    RegisterOut,
    RegisterRequest,
    PasswordResetConfirm,
    TokenOut,
    UserOut,
    UserUpdate,
)
from app.services.email_service import send_password_reset_email, send_verification_email
from app.services.security_event_service import record_security_event


def _email_taken(db: Session, email: str, exclude_id: int | None = None) -> bool:
    stmt = select(User.id).where(User.email == email)
    if exclude_id is not None:
        stmt = stmt.where(User.id != exclude_id)
    return db.scalar(stmt) is not None


def _refresh_token_hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def revoke_all_refresh_tokens(db: Session, user_id: int) -> None:
    now = utcnow()
    tokens = db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
    ).all()
    for token in tokens:
        token.revoked_at = now


def create_refresh_token(
    db: Session,
    user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, datetime]:
    raw_token = secrets.token_urlsafe(48)
    now = utcnow()
    expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=_refresh_token_hash(raw_token),
            expires_at=expires_at,
            ip_address=ip_address[:45] if ip_address else None,
            user_agent=user_agent[:500] if user_agent else None,
        )
    )
    db.commit()
    return raw_token, expires_at


def refresh_access_token(
    db: Session,
    raw_token: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> TokenOut:
    token_hash = _refresh_token_hash(raw_token)
    refresh_token = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    now = utcnow()
    if (
        refresh_token is None
        or refresh_token.revoked_at is not None
        or refresh_token.used_at is not None
        or refresh_token.expires_at <= now
    ):
        raise UnauthorizedError("Refresh token tidak valid atau sudah dicabut.", code="INVALID_REFRESH_TOKEN")

    user = db.get(User, refresh_token.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Akun tidak aktif atau tidak ditemukan.", code="INVALID_TOKEN")

    refresh_token.used_at = now
    db.commit()
    return issue_token(db, user, ip_address, user_agent)


def logout(db: Session, user: User, raw_token: str, ip_address: str | None = None, user_agent: str | None = None) -> None:
    token_hash = _refresh_token_hash(raw_token)
    refresh_token = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.user_id == user.id,
        )
    )
    if refresh_token is not None and refresh_token.revoked_at is None:
        refresh_token.revoked_at = utcnow()
        db.commit()
    record_security_event(
        db,
        user_id=user.id,
        event_type="LOGOUT",
        ip_address=ip_address,
        user_agent=user_agent,
    )


def list_active_refresh_tokens(db: Session, user_id: int) -> list[RefreshToken]:
    now = utcnow()
    return db.scalars(
        select(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.used_at.is_(None),
            RefreshToken.expires_at > now,
        )
        .order_by(RefreshToken.created_at.desc(), RefreshToken.id.desc())
    ).all()


def issue_token(
    db: Session,
    user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> TokenOut:
    access_token, expires_in = create_access_token(user.id, user.token_version)
    refresh_token, _ = create_refresh_token(db, user, ip_address, user_agent)
    return TokenOut(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=UserOut.model_validate(user),
    )


def register(db: Session, data: RegisterRequest) -> TokenOut | RegisterOut:
    if _email_taken(db, data.email):
        raise ConflictError("Email sudah terdaftar. Silakan login.", code="EMAIL_TAKEN")
    user = User(
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        is_email_verified=not settings.REQUIRE_EMAIL_VERIFICATION,
        email_verified_at=utcnow() if not settings.REQUIRE_EMAIL_VERIFICATION else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    if settings.REQUIRE_EMAIL_VERIFICATION:
        send_verification_email(user)
        return RegisterOut(
            message="Registrasi berhasil. Silakan verifikasi email sebelum login.",
            email_verification_required=True,
            user=UserOut.model_validate(user),
        )
    return issue_token(db, user)


def authenticate(
    db: Session,
    email: str,
    password: str,
    ip_address: str = "unknown",
    user_agent: str | None = None,
) -> TokenOut:
    login_rate_limiter.check(email, ip_address)
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not verify_password(password, user.password_hash):
        login_rate_limiter.record_failure(email, ip_address)
        record_security_event(
            db,
            user_id=None,
            event_type="LOGIN_FAILED",
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"email": email.strip().lower()},
        )
        raise UnauthorizedError("Email atau password salah.", code="INVALID_CREDENTIALS")
    if not user.is_active:
        login_rate_limiter.record_failure(email, ip_address)
        record_security_event(db, user_id=user.id, event_type="LOGIN_FAILED", success=False, ip_address=ip_address, user_agent=user_agent, details={"reason": "inactive"})
        raise UnauthorizedError("Akun dinonaktifkan.", code="USER_INACTIVE")
    if settings.REQUIRE_EMAIL_VERIFICATION and not user.is_email_verified:
        login_rate_limiter.record_failure(email, ip_address)
        record_security_event(db, user_id=user.id, event_type="LOGIN_FAILED", success=False, ip_address=ip_address, user_agent=user_agent, details={"reason": "email_not_verified"})
        raise ForbiddenError(
            "Email belum diverifikasi. Periksa kotak masuk Anda atau kirim ulang tautan verifikasi.",
            code="EMAIL_NOT_VERIFIED",
        )
    login_rate_limiter.record_success(email, ip_address)
    from app.models.security_event import SecurityEvent

    prior_login = db.scalar(
        select(SecurityEvent)
        .where(
            SecurityEvent.user_id == user.id,
            SecurityEvent.event_type == "LOGIN_SUCCESS",
            SecurityEvent.success == True,  # noqa: E712
        )
        .order_by(SecurityEvent.created_at.desc(), SecurityEvent.id.desc())
    )
    record_security_event(
        db,
        user_id=user.id,
        event_type="LOGIN_SUCCESS",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if prior_login is None or (
        prior_login.ip_address != ip_address or prior_login.user_agent != (user_agent[:500] if user_agent else None)
    ):
        record_security_event(
            db,
            user_id=user.id,
            event_type="LOGIN_NEW_DEVICE",
            ip_address=ip_address,
            user_agent=user_agent,
            details={"message": "Login dari IP atau perangkat yang berbeda."},
        )
    return issue_token(db, user, ip_address, user_agent)


def verify_email(db: Session, token: str) -> None:
    user_id = decode_email_verification_token(token)
    if user_id is None:
        raise BadRequestError("Tautan verifikasi tidak valid atau sudah kedaluwarsa.", code="INVALID_VERIFICATION_TOKEN")
    user = db.get(User, user_id)
    if user is None:
        raise BadRequestError("Pengguna untuk tautan verifikasi tidak ditemukan.", code="USER_NOT_FOUND")
    if not user.is_email_verified:
        user.is_email_verified = True
        user.email_verified_at = utcnow()
        db.commit()


def resend_verification(db: Session, email: str) -> None:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is not None and not user.is_email_verified and user.is_active:
        send_verification_email(user)


def request_password_reset(db: Session, email: str) -> None:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not user.is_active:
        return

    now = utcnow()
    old_tokens = db.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
    ).all()
    for old_token in old_tokens:
        old_token.used_at = now

    raw_token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=now + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
    )
    db.add(reset_token)
    db.commit()
    send_password_reset_email(user, raw_token)


def reset_password(
    db: Session,
    data: PasswordResetConfirm,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    token_hash = hashlib.sha256(data.token.encode("utf-8")).hexdigest()
    reset_token = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
        )
    )
    now = utcnow()
    if reset_token is None or reset_token.expires_at <= now:
        raise BadRequestError(
            "Token reset password tidak valid atau sudah kedaluwarsa.",
            code="INVALID_RESET_TOKEN",
        )

    user = db.get(User, reset_token.user_id)
    if user is None or not user.is_active:
        raise BadRequestError("Pengguna untuk token reset tidak ditemukan.", code="USER_NOT_FOUND")

    try:
        validate_password(data.new_password)
    except ValueError as exc:
        raise BadRequestError(str(exc), code="WEAK_PASSWORD")
    user.password_hash = hash_password(data.new_password)
    reset_token.used_at = now
    user.token_version += 1
    revoke_all_refresh_tokens(db, user.id)

    all_active_tokens = db.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
    ).all()
    for active_token in all_active_tokens:
        active_token.used_at = now
    record_security_event(
        db,
        user_id=user.id,
        event_type="PASSWORD_CHANGED",
        ip_address=ip_address,
        user_agent=user_agent,
        details={"method": "forgot_password_reset"},
    )
    db.commit()


def update_profile(
    db: Session,
    user: User,
    data: UserUpdate,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> User:
    if data.email and data.email != user.email:
        if _email_taken(db, data.email, exclude_id=user.id):
            raise ConflictError("Email sudah dipakai akun lain.", code="EMAIL_TAKEN")
        old_email = user.email
        user.email = data.email
        if settings.REQUIRE_EMAIL_VERIFICATION:
            user.is_email_verified = False
            user.email_verified_at = None
            db.commit()
            db.refresh(user)
            send_verification_email(user)
        record_security_event(
            db,
            user_id=user.id,
            event_type="EMAIL_UPDATED",
            ip_address=ip_address,
            user_agent=user_agent,
            details={"old_email": old_email, "new_email": data.email},
        )
    if data.full_name:
        user.full_name = " ".join(data.full_name.split())
    db.commit()
    db.refresh(user)
    return user


def change_password(
    db: Session,
    user: User,
    data: PasswordChange,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    if not verify_password(data.current_password, user.password_hash):
        record_security_event(
            db,
            user_id=user.id,
            event_type="PASSWORD_CHANGE_FAILED",
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise BadRequestError("Password lama salah.", code="WRONG_PASSWORD")
    try:
        validate_password(data.new_password)
    except ValueError as exc:
        raise BadRequestError(str(exc), code="WEAK_PASSWORD")
    user.password_hash = hash_password(data.new_password)
    user.token_version += 1
    revoke_all_refresh_tokens(db, user.id)
    record_security_event(
        db,
        user_id=user.id,
        event_type="PASSWORD_CHANGED",
        ip_address=ip_address,
        user_agent=user_agent,
        details={"method": "profile"},
    )
    db.commit()
