from pydantic import BaseModel, Field

from app.schemas.category import CategoryBrief
from app.schemas.common import LocalDateTime


class PredictionOut(BaseModel):
    category_id: int | None = None
    category: CategoryBrief | None = None
    confidence_score: float | None = Field(default=None, description="0..1")
    confidence_percent: int | None = Field(default=None, description="0..100, siap ditampilkan")
    prediction_source: str | None = Field(
        default=None, description="user_history | keyword_rules | ml_model"
    )
    needs_review: bool = Field(description="true = tandai kuning 'Periksa' di layar koreksi")


class ScanItemOut(PredictionOut):
    index: int
    item_name: str
    quantity: int = 1
    unit_price: float | None = None
    item_price: float | None = None
    predicted_category_id: int | None = Field(
        default=None, description="Kirim balik saat menyimpan agar koreksi pengguna tercatat"
    )


class ScanOut(BaseModel):
    scan_id: str = Field(description="Kirim di POST /receipts agar foto ikut tersimpan")
    image_url: str
    merchant_name: str | None = None
    transaction_date: LocalDateTime | None = None
    total_amount: float | None = None
    items_total: float
    total_matches: bool | None = Field(
        description="Apakah total struk sama dengan jumlah harga barang (null jika total tak terbaca)"
    )
    review_count: int = Field(description="Jumlah barang yang perlu diperiksa pengguna")
    items: list[ScanItemOut]
    warnings: list[str]
    raw_text: str


class ClassifyRequest(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=100, examples=[["SUSU UHT 1L", "RINSO 800G"]])


class ClassifyItemOut(PredictionOut):
    text: str
