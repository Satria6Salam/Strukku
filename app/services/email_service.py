import logging
import smtplib
from email.message import EmailMessage
from urllib.parse import urlencode

from app.core.config import settings
from app.core.security import create_email_verification_token
from app.models import User

logger = logging.getLogger("strukku")


def build_verification_url(user: User) -> str:
    token = create_email_verification_token(user.id)
    base_url = settings.PUBLIC_BASE_URL.rstrip("/")
    return f"{base_url}/api/v1/auth/verify-email?{urlencode({'token': token})}"


def send_verification_email(user: User) -> bool:
    verification_url = build_verification_url(user)

    if not settings.SMTP_HOST:
        logger.info(
            "Email verifikasi tidak dikirim melalui SMTP. Tautan pengujian untuk %s: %s",
            user.email,
            verification_url,
        )
        return False

    sender = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME or "no-reply@strukku.local"
    message = EmailMessage()
    message["Subject"] = "Verifikasi email STRUKKU"
    message["From"] = sender
    message["To"] = user.email
    message.set_content(
        "Verifikasi alamat email STRUKKU Anda dengan membuka tautan berikut:\n\n"
        f"{verification_url}\n\n"
        "Jika Anda tidak membuat akun ini, abaikan email ini."
    )
    message.add_alternative(
        f"""
<html><body>
<p>Verifikasi alamat email STRUKKU Anda:</p>
<p><a href="{verification_url}">Verifikasi Email</a></p>
<p>Jika Anda tidak membuat akun ini, abaikan email ini.</p>
</body></html>
""",
        subtype="html",
    )

    try:
        if settings.SMTP_USE_SSL:
            smtp: smtplib.SMTP | smtplib.SMTP_SSL = smtplib.SMTP_SSL(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=settings.SMTP_TIMEOUT_SECONDS,
            )
        else:
            smtp = smtplib.SMTP(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=settings.SMTP_TIMEOUT_SECONDS,
            )
        with smtp:
            if settings.SMTP_USE_TLS and not settings.SMTP_USE_SSL:
                smtp.starttls()
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)
        return True
    except (smtplib.SMTPException, OSError, TimeoutError) as exc:
        logger.error("Gagal mengirim email verifikasi ke %s: %s", user.email, exc.__class__.__name__)
        return False


def build_password_reset_url(token: str) -> str:
    base_url = settings.PUBLIC_BASE_URL.rstrip("/")
    return f"{base_url}/api/v1/auth/reset-password?{urlencode({'token': token})}"


def send_password_reset_email(user: User, token: str) -> bool:
    reset_url = build_password_reset_url(token)

    if not settings.SMTP_HOST:
        logger.info(
            "Email reset password tidak dikirim melalui SMTP. Tautan pengujian untuk %s: %s",
            user.email,
            reset_url,
        )
        return False

    sender = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME or "no-reply@strukku.local"
    message = EmailMessage()
    message["Subject"] = "Reset password STRUKKU"
    message["From"] = sender
    message["To"] = user.email
    message.set_content(
        "Permintaan reset password STRUKKU diterima.\n\n"
        f"Gunakan tautan berikut dalam {settings.PASSWORD_RESET_EXPIRE_MINUTES} menit:\n"
        f"{reset_url}\n\n"
        "Jika Anda tidak meminta reset password, abaikan email ini."
    )
    message.add_alternative(
        f"""
<html><body>
<p>Permintaan reset password STRUKKU diterima.</p>
<p><a href="{reset_url}">Reset Password</a></p>
<p>Tautan berlaku {settings.PASSWORD_RESET_EXPIRE_MINUTES} menit dan hanya dapat digunakan sekali.</p>
</body></html>
""",
        subtype="html",
    )

    try:
        if settings.SMTP_USE_SSL:
            smtp: smtplib.SMTP | smtplib.SMTP_SSL = smtplib.SMTP_SSL(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=settings.SMTP_TIMEOUT_SECONDS,
            )
        else:
            smtp = smtplib.SMTP(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=settings.SMTP_TIMEOUT_SECONDS,
            )
        with smtp:
            if settings.SMTP_USE_TLS and not settings.SMTP_USE_SSL:
                smtp.starttls()
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)
        return True
    except (smtplib.SMTPException, OSError, TimeoutError) as exc:
        logger.error("Gagal mengirim email reset password ke %s: %s", user.email, exc.__class__.__name__)
        return False
