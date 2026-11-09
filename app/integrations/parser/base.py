from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ParsedItem:
    name: str
    price: float | None  # harga total baris
    quantity: int = 1
    unit_price: float | None = None


@dataclass
class ParsedReceipt:
    merchant_name: str | None = None
    transaction_date: datetime | None = None
    total_amount: float | None = None
    items: list[ParsedItem] = field(default_factory=list)


class ReceiptParser(ABC):
    """Kontrak pengubah teks OCR menjadi data struk terstruktur."""

    name: str = "base"

    @abstractmethod
    def parse(self, text: str) -> ParsedReceipt:
        ...
