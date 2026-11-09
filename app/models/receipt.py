from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.timeutils import utcnow
from app.db.session import Base


class Receipt(Base):
    __tablename__ = "receipts"
    __table_args__ = (
        Index("ix_receipts_user_id_transaction_date", "user_id", "transaction_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    merchant_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    transaction_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    # Kolom DB tetap bernama image_url (sesuai ERD) tetapi isinya adalah kunci
    # file di storage. URL untuk frontend dibentuk oleh API.
    image_key: Mapped[str | None] = mapped_column("image_url", String(500), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=True)

    user = relationship("User", back_populates="receipts")
    items = relationship(
        "ReceiptItem",
        back_populates="receipt",
        cascade="all, delete-orphan",
        order_by="ReceiptItem.id",
    )
