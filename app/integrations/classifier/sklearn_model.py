import logging
from pathlib import Path

import joblib

from app.integrations.classifier.base import ClassificationContext, ItemClassifier, Prediction
from app.integrations.classifier.text_normalizer import TextNormalizer

logger = logging.getLogger("strukku")


class SklearnModelClassifier(ItemClassifier):
    """Model TF-IDF + Multinomial Naive Bayes (file .joblib dari tim ML).

    Format yang diterima:
    - sklearn Pipeline yang punya predict()/predict_proba(), atau
    - dict berisi `vectorizer`/`tfidf` dan `classifier`/`model`/`nb`.
    Untuk mengganti model: taruh file baru di folder `models/` lalu ubah
    MODEL_PATH di .env. Tidak perlu mengubah kode selama formatnya sama.
    """

    name = "ml_model"

    def __init__(self, model_path: Path, normalizer: TextNormalizer | None = None):
        self.model_path = model_path
        self.normalizer = normalizer or TextNormalizer()
        self.pipeline = None
        self.vectorizer = None
        self.classifier = None
        self.error: str | None = None
        self._load()

    def _load(self) -> None:
        if not self.model_path.exists():
            self.error = f"File model tidak ditemukan: {self.model_path}"
            logger.warning(self.error)
            return
        try:
            artifact = joblib.load(self.model_path)
        except Exception as exc:  # versi scikit-learn tidak cocok, file rusak, dll.
            self.error = f"Gagal memuat model: {exc}"
            logger.error(self.error)
            return
        if hasattr(artifact, "predict"):
            self.pipeline = artifact
        elif isinstance(artifact, dict):
            self.vectorizer = artifact.get("vectorizer") or artifact.get("tfidf")
            self.classifier = artifact.get("classifier") or artifact.get("model") or artifact.get("nb")
        if not self.is_ready:
            self.error = "Format model tidak dikenali (butuh Pipeline atau dict vectorizer+classifier)."

    @property
    def is_ready(self) -> bool:
        return self.pipeline is not None or (self.vectorizer is not None and self.classifier is not None)

    @property
    def classes(self) -> list[str]:
        source = self.pipeline if self.pipeline is not None else self.classifier
        values = getattr(source, "classes_", None) if source is not None else None
        return [str(v) for v in values] if values is not None else []

    def predict_many(self, texts: list[str], ctx: ClassificationContext) -> list[Prediction | None]:
        if not self.is_ready or not texts:
            return [None] * len(texts)
        prepared = [self.normalizer.normalize(t) or t for t in texts]
        if self.pipeline is not None:
            model, features = self.pipeline, prepared
        else:
            model, features = self.classifier, self.vectorizer.transform(prepared)

        labels = model.predict(features)
        confidences: list[float | None] = [None] * len(texts)
        if hasattr(model, "predict_proba"):
            confidences = [float(row.max()) for row in model.predict_proba(features)]
        return [
            Prediction(str(label), conf, self.name) for label, conf in zip(labels, confidences)
        ]

    def status(self) -> dict:
        return {
            "name": self.name,
            "ready": self.is_ready,
            "model_file": self.model_path.name,
            "classes": self.classes,
            "message": self.error or "Model berhasil dimuat",
        }
