from abc import ABC, abstractmethod

from PIL import Image


class OCREngine(ABC):
    """Kontrak mesin OCR.

    Untuk mengganti Tesseract dengan layanan lain (mis. Google Vision),
    buat kelas turunan ini lalu daftarkan di `app/integrations/providers.py`.
    """

    name: str = "base"

    @abstractmethod
    def extract_text(self, image: Image.Image) -> str:
        """Kembalikan teks mentah dari gambar struk."""

    def status(self) -> dict:
        return {"engine": self.name, "ready": True, "message": "OK"}
