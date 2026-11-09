import json
import logging
import re
from pathlib import Path

from app.integrations.classifier.base import ClassificationContext, ItemClassifier, Prediction
from app.integrations.classifier.text_normalizer import TextNormalizer

logger = logging.getLogger("strukku")


class KeywordRuleClassifier(ItemClassifier):
    """Mencocokkan kata kunci dari `app/data/keyword_rules.json`.

    Kata kunci terpanjang yang cocok menang, sehingga frasa spesifik
    ("sabun cuci piring") mengalahkan kata umum ("sabun").
    """

    name = "keyword_rules"

    def __init__(self, rules_path: Path, normalizer: TextNormalizer | None = None):
        self.rules_path = rules_path
        self.rules: list[tuple[re.Pattern, str, int]] = []
        self.confidence = 0.9
        self.normalizer = normalizer or TextNormalizer()
        self.error: str | None = None
        self._load()

    def _load(self) -> None:
        if not self.rules_path.exists():
            self.error = f"File aturan tidak ditemukan: {self.rules_path}"
            return
        try:
            data = json.loads(self.rules_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            self.error = f"keyword_rules.json tidak valid: {exc}"
            logger.error(self.error)
            return
        self.confidence = float(data.get("confidence", 0.9))
        self.normalizer = TextNormalizer(data.get("abbreviations", {}))
        for category, keywords in data.get("categories", {}).items():
            for keyword in keywords:
                kw = self.normalizer.basic(keyword)
                if kw:
                    pattern = re.compile(rf"(?<![0-9a-z]){re.escape(kw)}(?![0-9a-z])")
                    self.rules.append((pattern, category, len(kw)))
        self.rules.sort(key=lambda rule: rule[2], reverse=True)

    def predict_one(self, text: str) -> Prediction | None:
        normalized = self.normalizer.normalize(text)
        for pattern, category, _ in self.rules:  # sudah terurut dari terpanjang
            if pattern.search(normalized):
                return Prediction(category, self.confidence, self.name)
        return None

    def predict_many(self, texts: list[str], ctx: ClassificationContext) -> list[Prediction | None]:
        return [self.predict_one(t) for t in texts]

    def status(self) -> dict:
        return {
            "name": self.name,
            "ready": self.error is None,
            "rules": len(self.rules),
            "message": self.error or "OK",
        }
