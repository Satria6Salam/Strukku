from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token_claims
from app.db.session import get_db
from app.integrations.classifier.chain import ClassifierChain
from app.integrations.ocr.base import OCREngine
from app.integrations.parser.base import ReceiptParser
from app.integrations.providers import get_classifier, get_ocr_engine, get_parser, get_storage
from app.integrations.storage.base import StorageBackend
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/token", auto_error=False)

DB = Annotated[Session, Depends(get_db)]


def get_current_user(db: DB, token: Annotated[str | None, Depends(oauth2_scheme)]) -> User:
    if not token:
        raise UnauthorizedError("Silakan login terlebih dahulu.", code="NOT_AUTHENTICATED")
    user_id, token_version = decode_access_token_claims(token)
    user = db.get(User, user_id) if user_id else None
    if user is None or not user.is_active:
        raise UnauthorizedError("Sesi tidak valid atau sudah berakhir. Silakan login ulang.", code="INVALID_TOKEN")
    if token_version != user.token_version:
        raise UnauthorizedError("Token telah dicabut. Silakan login ulang.", code="TOKEN_REVOKED")
    if settings.REQUIRE_EMAIL_VERIFICATION and not user.is_email_verified:
        raise UnauthorizedError(
            "Email belum diverifikasi. Silakan verifikasi email terlebih dahulu.",
            code="EMAIL_NOT_VERIFIED",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
OCR = Annotated[OCREngine, Depends(get_ocr_engine)]
Parser = Annotated[ReceiptParser, Depends(get_parser)]
Classifier = Annotated[ClassifierChain, Depends(get_classifier)]
Storage = Annotated[StorageBackend, Depends(get_storage)]
