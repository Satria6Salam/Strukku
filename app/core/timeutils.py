"""Utilitas waktu.

Aturan sederhana yang dipakai di seluruh backend:
- `created_at` / `updated_at` disimpan dalam UTC (tanpa info zona) dan dikirim
  ke frontend dengan akhiran zona UTC.
- `transaction_date` adalah jam dinding lokal (WIB) seperti yang tercetak di
  struk, dan dipakai untuk pengelompokan per bulan.
"""
import re
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.core.config import settings

MONTH_NAMES_ID = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]
_MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")


def local_tz() -> ZoneInfo:
    return ZoneInfo(settings.TIMEZONE)


def utcnow() -> datetime:
    """Waktu UTC sekarang tanpa tzinfo (untuk kolom created_at/updated_at)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def local_now() -> datetime:
    """Jam dinding lokal sekarang tanpa tzinfo."""
    return datetime.now(local_tz()).replace(tzinfo=None)


def to_local_naive(value: datetime | None) -> datetime | None:
    """Ubah datetime ber-zona (mis. dari Flutter `toUtc()`) menjadi jam lokal."""
    if value is None or value.tzinfo is None:
        return value
    return value.astimezone(local_tz()).replace(tzinfo=None)


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def parse_month(value: str | None) -> date:
    """'2026-10' -> date(2026, 10, 1). None -> bulan berjalan."""
    if not value:
        now = local_now()
        return date(now.year, now.month, 1)
    match = _MONTH_RE.match(value)
    if not match or not 1 <= int(match.group(2)) <= 12:
        from app.core.exceptions import BadRequestError

        raise BadRequestError("Format bulan harus YYYY-MM, contoh 2026-10.", code="INVALID_MONTH")
    return date(int(match.group(1)), int(match.group(2)), 1)


def shift_month(month: date, delta: int) -> date:
    index = month.year * 12 + (month.month - 1) + delta
    return date(index // 12, index % 12 + 1, 1)


def month_range(month: date) -> tuple[datetime, datetime]:
    """Rentang [awal bulan, awal bulan berikutnya)."""
    start = datetime(month.year, month.month, 1)
    nxt = shift_month(month, 1)
    return start, datetime(nxt.year, nxt.month, 1)


def month_key(month: date) -> str:
    return f"{month.year:04d}-{month.month:02d}"


def month_label(month: date) -> str:
    return f"{MONTH_NAMES_ID[month.month - 1]} {month.year}"
