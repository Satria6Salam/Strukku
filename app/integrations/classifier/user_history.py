from sqlalchemy import func, select

from app.integrations.classifier.base import ClassificationContext, ItemClassifier, Prediction
from app.models import Category, Receipt, ReceiptItem


class UserHistoryClassifier(ItemClassifier):
    """Memakai koreksi pengguna sebelumnya.

    Jika pengguna pernah mengubah kategori "SUSU UHT 1L" menjadi Minuman,
    scan berikutnya dengan nama barang yang sama langsung memakai Minuman.
    """

    name = "user_history"
    confidence = 0.99

    def predict_many(self, texts: list[str], ctx: ClassificationContext) -> list[Prediction | None]:
        if ctx.db is None or ctx.user_id is None or not texts:
            return [None] * len(texts)
        keys = {t.strip().lower() for t in texts if t.strip()}
        if not keys:
            return [None] * len(texts)
        stmt = (
            select(func.lower(ReceiptItem.item_name), Category.name)
            .join(Receipt, Receipt.id == ReceiptItem.receipt_id)
            .join(Category, Category.id == ReceiptItem.category_id)
            .where(
                Receipt.user_id == ctx.user_id,
                ReceiptItem.is_user_corrected.is_(True),
                func.lower(ReceiptItem.item_name).in_(keys),
            )
            .order_by(ReceiptItem.id.desc())
        )
        latest: dict[str, str] = {}
        for name, category in ctx.db.execute(stmt):
            latest.setdefault(name, category)  # yang terbaru menang
        return [
            Prediction(latest[t.strip().lower()], self.confidence, self.name)
            if t.strip().lower() in latest
            else None
            for t in texts
        ]
