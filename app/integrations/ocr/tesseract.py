import shutil
from pathlib import Path

import pytesseract
from PIL import Image, ImageEnhance, ImageOps

from app.integrations.ocr.base import OCREngine


class TesseractOCR(OCREngine):
    name = "tesseract"

    def __init__(self, tesseract_cmd: str = "", lang: str = "ind+eng", psm: int = 4):
        self.lang = lang
        self.psm = psm
        if tesseract_cmd and Path(tesseract_cmd).exists():
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    @staticmethod
    def preprocess(image: Image.Image) -> Image.Image:
        image = ImageOps.exif_transpose(image)  # foto HP sering tersimpan miring
        image = ImageOps.grayscale(image)
        # Teks struk kecil; perbesar gambar beresolusi rendah agar terbaca.
        if image.width < 1000:
            scale = 1000 / image.width
            image = image.resize((1000, int(image.height * scale)), Image.LANCZOS)
        image = ImageOps.autocontrast(image, cutoff=1)
        return ImageEnhance.Sharpness(image).enhance(1.5)

    def extract_text(self, image: Image.Image) -> str:
        prepared = self.preprocess(image)
        return pytesseract.image_to_string(
            prepared, lang=self.lang, config=f"--oem 3 --psm {self.psm}"
        ).strip()

    def status(self) -> dict:
        cmd = pytesseract.pytesseract.tesseract_cmd
        if not (Path(cmd).exists() or shutil.which(cmd)):
            return {
                "engine": self.name,
                "ready": False,
                "message": "Tesseract tidak ditemukan. Instal Tesseract atau isi TESSERACT_CMD di .env.",
            }
        try:
            version = str(pytesseract.get_tesseract_version())
            langs = set(pytesseract.get_languages(config=""))
        except Exception as exc:  # pragma: no cover - tergantung instalasi
            return {"engine": self.name, "ready": False, "message": f"Tesseract error: {exc}"}
        missing = [code for code in self.lang.split("+") if code not in langs]
        if missing:
            return {
                "engine": self.name,
                "ready": False,
                "version": version,
                "message": f"Data bahasa OCR belum terpasang: {', '.join(missing)}",
            }
        return {"engine": self.name, "ready": True, "version": version, "languages": self.lang, "message": "OK"}
