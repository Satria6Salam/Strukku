from datetime import datetime
from typing import Annotated, Generic, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict

from app.core.timeutils import as_utc, to_local_naive

T = TypeVar("T")

# Dikirim ke frontend dengan zona UTC (akhiran "Z"/+00:00).
UTCDateTime = Annotated[datetime, AfterValidator(as_utc)]
# Waktu transaksi: jika dikirim dengan zona, diubah ke jam lokal (WIB).
LocalDateTime = Annotated[datetime, AfterValidator(to_local_naive)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class MessageOut(BaseModel):
    message: str


class ErrorOut(BaseModel):
    detail: str
    code: str
