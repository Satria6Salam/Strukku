from decimal import Decimal

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ReceiptItem(Base):
    __tablename__ = "receipt_items"
    __table_args__ = (
        Index("ix_receipt_items_receipt_id", "receipt_id"),
        Index("ix_receipt_items_category_id", "category_id"),
        Index("ix_receipt_items_receipt_category", "receipt_id", "category_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    receipt_id: Mapped[int] = mapped_column(ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    # Harga total baris (qty x harga satuan), sesuai yang tercetak di struk.
    item_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_user_corrected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Kategori asli dari prediksi sistem & sumbernya, untuk evaluasi/retraining.
    predicted_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", name="fk_receipt_items_predicted_category_id_categories"),
        nullable=True,
    )
    prediction_source: Mapped[str | None] = mapped_column(String(30), nullable=True)

    receipt = relationship("Receipt", back_populates="items")
    category = relationship("Category", foreign_keys=[category_id], lazy="joined")
    predicted_category = relationship("Category", foreign_keys=[predicted_category_id])
