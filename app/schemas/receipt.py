from pydantic import BaseModel, Field, field_validator

from app.schemas.category import CategoryBrief
from app.schemas.common import LocalDateTime, ORMModel, UTCDateTime


# ----------------------------------------------------------------- input
class ReceiptItemIn(BaseModel):
    item_name: str = Field(min_length=1, max_length=255, examples=["ROTI TAWAR 500G"])
    quantity: int = Field(default=1, ge=1, le=9999)
    item_price: float | None = Field(default=None, ge=0, description="Harga total baris (qty x satuan)")
    category_id: int | None = Field(default=None, description="Kategori final pilihan pengguna")
    predicted_category_id: int | None = Field(
        default=None, description="Kategori hasil scan (salin dari respons /scans)"
    )
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    prediction_source: str | None = Field(default=None, max_length=30)
    is_user_corrected: bool | None = Field(
        default=None,
        description="Kosongkan agar dihitung otomatis: true jika category_id berbeda dari predicted_category_id",
    )

    @field_validator("item_name")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Nama barang wajib diisi")
        return value


class ReceiptBase(BaseModel):
    merchant_name: str | None = Field(default=None, max_length=200, examples=["INDOMARET"])
    transaction_date: LocalDateTime | None = Field(
        default=None, description="Kosong = waktu sekarang", examples=["2026-10-21T14:30:00"]
    )
    total_amount: float | None = Field(
        default=None, ge=0, description="Kosong = jumlah harga semua barang"
    )
    items: list[ReceiptItemIn] = Field(min_length=1)


class ReceiptCreate(ReceiptBase):
    scan_id: str | None = Field(default=None, description="scan_id dari POST /scans agar foto ikut tersimpan")
    raw_text: str | None = Field(default=None, description="Teks OCR (opsional, untuk evaluasi)")


class ReceiptUpdate(ReceiptBase):
    """Mengganti seluruh isi struk (header + daftar barang)."""


class ReceiptItemUpdate(BaseModel):
    item_name: str | None = Field(default=None, min_length=1, max_length=255)
    quantity: int | None = Field(default=None, ge=1, le=9999)
    item_price: float | None = Field(default=None, ge=0)
    category_id: int | None = None


# ---------------------------------------------------------------- output
class ReceiptItemOut(ORMModel):
    id: int
    item_name: str
    quantity: int = 1
    item_price: float | None = None
    category_id: int | None = None
    category: CategoryBrief | None = None
    predicted_category_id: int | None = None
    prediction_source: str | None = None
    confidence_score: float | None = None
    is_user_corrected: bool = False


class ReceiptSummaryOut(BaseModel):
    id: int
    merchant_name: str | None
    transaction_date: LocalDateTime | None
    total_amount: float | None
    item_count: int
    image_url: str | None = Field(description="Path gambar (butuh header Authorization)")
    main_category: CategoryBrief | None = Field(
        default=None, description="Kategori dengan nominal terbesar di struk ini"
    )
    created_at: UTCDateTime | None


class ReceiptOut(ReceiptSummaryOut):
    items_total: float
    updated_at: UTCDateTime | None = None
    items: list[ReceiptItemOut]
