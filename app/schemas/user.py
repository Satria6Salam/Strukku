from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from app.core.password_policy import validate_password

from app.schemas.common import ORMModel, UTCDateTime


def _clean_email(value: str) -> str:
    return value.strip().lower()


class UserOut(ORMModel):
    id: int
    email: str
    full_name: str
    created_at: UTCDateTime | None = None
    is_email_verified: bool = False


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150, examples=["Reza"])
    email: EmailStr = Field(examples=["reza@gmail.com"])
    password: str = Field(min_length=8, max_length=64, examples=["S!N7mQ2x"])
    password_confirmation: str | None = Field(
        default=None, description="Opsional. Jika dikirim harus sama dengan password."
    )

    _email = field_validator("email")(_clean_email)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        validate_password(value)
        return value

    @field_validator("full_name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Nama minimal 2 karakter")
        return value

    @model_validator(mode="after")
    def _check_confirmation(self):
        if self.password_confirmation is not None and self.password_confirmation != self.password:
            raise ValueError("Konfirmasi password tidak sama")
        return self


class LoginRequest(BaseModel):
    email: EmailStr = Field(examples=["reza@gmail.com"])
    password: str = Field(min_length=1, max_length=64, examples=["S!N7mQ2x"])

    _email = field_validator("email")(_clean_email)


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=512)


class RefreshTokenOut(ORMModel):
    id: int
    expires_at: UTCDateTime | None = None
    revoked_at: UTCDateTime | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: UTCDateTime | None = None


class RegisterOut(BaseModel):
    message: str
    email_verification_required: bool
    user: UserOut


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    new_password: str = Field(min_length=8, max_length=64)
    new_password_confirmation: str | None = Field(default=None)

    @field_validator("new_password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        validate_password(value)
        return value

    @model_validator(mode="after")
    def _check_confirmation(self):
        if (
            self.new_password_confirmation is not None
            and self.new_password_confirmation != self.new_password
        ):
            raise ValueError("Konfirmasi password tidak sama")
        return self


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    email: EmailStr | None = None

    @field_validator("email")
    @classmethod
    def _email(cls, value):
        return _clean_email(value) if value else value


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=64)
    new_password: str = Field(min_length=8, max_length=64)

    @field_validator("new_password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        validate_password(value)
        return value


class PasswordStrengthRequest(BaseModel):
    password: str = Field(min_length=1, max_length=64)


class PasswordStrengthOut(BaseModel):
    score: int = Field(ge=0, le=5)
    level: str
    label: str
    is_common: bool
    suggestions: list[str]


class SecurityEventOut(ORMModel):
    id: int
    event_type: str
    success: bool
    ip_address: str | None = None
    user_agent: str | None = None
    details: str | None = None
    created_at: UTCDateTime | None = None
