from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy.orm import Session


@dataclass
class Prediction:
    category_key: str  # sama dengan Category.name / label model
    confidence: float | None
    source: str  # user_history | keyword_rules | ml_model | ...


@dataclass
class ClassificationContext:
    db: Session | None = None
    user_id: int | None = None


class ItemClassifier(ABC):
    """Kontrak penentu kategori nama barang.

    Beberapa classifier dirangkai berurutan (lihat `chain.py`); classifier
    mengembalikan None untuk teks yang tidak bisa ia tangani sehingga
    classifier berikutnya mencoba.
    """

    name: str = "base"

    @abstractmethod
    def predict_many(self, texts: list[str], ctx: ClassificationContext) -> list[Prediction | None]:
        ...

    def status(self) -> dict:
        return {"name": self.name, "ready": True}
