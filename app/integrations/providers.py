"""Titik pusat pemilihan implementasi (OCR, parser, classifier, storage).

Untuk menambah implementasi baru:
1. Buat kelas turunan dari base class yang sesuai di folder integrations/.
2. Daftarkan di dictionary *_REGISTRY di bawah.
3. Pilih lewat .env (OCR_ENGINE, STORAGE_BACKEND, CLASSIFIER_PIPELINE).

Semua fungsi `get_*` dipakai sebagai dependency FastAPI, sehingga di
pengujian bisa diganti dengan `app.dependency_overrides`.
"""
import json
from functools import lru_cache

from app.core.config import settings
from app.integrations.classifier.base import ItemClassifier
from app.integrations.classifier.chain import ClassifierChain
from app.integrations.classifier.keyword_rules import KeywordRuleClassifier
from app.integrations.classifier.sklearn_model import SklearnModelClassifier
from app.integrations.classifier.text_normalizer import TextNormalizer
from app.integrations.classifier.user_history import UserHistoryClassifier
from app.integrations.ocr.base import OCREngine
from app.integrations.ocr.tesseract import TesseractOCR
from app.integrations.parser.base import ReceiptParser
from app.integrations.parser.regex_parser import RegexReceiptParser
from app.integrations.storage.base import StorageBackend
from app.integrations.storage.local import LocalStorage
from app.integrations.storage.supabase import SupabaseStorage

OCR_REGISTRY = {
    "tesseract": lambda: TesseractOCR(settings.TESSERACT_CMD, settings.OCR_LANG, settings.OCR_PSM),
}
STORAGE_REGISTRY = {
    "local": lambda: LocalStorage(settings.path(settings.UPLOAD_DIR)),
    "supabase": lambda: SupabaseStorage(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY,
        settings.SUPABASE_STORAGE_BUCKET,
        settings.SUPABASE_SIGNED_URL_EXPIRY_SECONDS,
    ),
}
PARSER_REGISTRY = {
    "regex": RegexReceiptParser,
}


def _normalizer() -> TextNormalizer:
    try:
        data = json.loads(settings.path(settings.KEYWORD_RULES_PATH).read_text(encoding="utf-8"))
        return TextNormalizer(data.get("abbreviations", {}))
    except (OSError, ValueError):
        return TextNormalizer()


CLASSIFIER_REGISTRY = {
    "user_history": UserHistoryClassifier,
    "keyword_rules": lambda: KeywordRuleClassifier(settings.path(settings.KEYWORD_RULES_PATH)),
    "ml_model": lambda: get_ml_model(),
}


def _pick(registry: dict, key: str, label: str):
    if key not in registry:
        raise ValueError(f"{label} '{key}' tidak dikenal. Pilihan: {', '.join(registry)}")
    return registry[key]()


@lru_cache
def get_ocr_engine() -> OCREngine:
    return _pick(OCR_REGISTRY, settings.OCR_ENGINE, "OCR_ENGINE")


@lru_cache
def get_storage() -> StorageBackend:
    return _pick(STORAGE_REGISTRY, settings.STORAGE_BACKEND, "STORAGE_BACKEND")


@lru_cache
def get_parser() -> ReceiptParser:
    return _pick(PARSER_REGISTRY, "regex", "PARSER")


@lru_cache
def get_ml_model() -> SklearnModelClassifier:
    return SklearnModelClassifier(settings.path(settings.MODEL_PATH), _normalizer())


@lru_cache
def get_classifier() -> ClassifierChain:
    classifiers: list[ItemClassifier] = [
        _pick(CLASSIFIER_REGISTRY, name, "CLASSIFIER_PIPELINE") for name in settings.classifier_pipeline
    ]
    return ClassifierChain(classifiers)
