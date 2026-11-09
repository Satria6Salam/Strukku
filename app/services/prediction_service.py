"""Menjalankan rangkaian classifier dan mengemasnya untuk frontend."""
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.classifier.base import ClassificationContext
from app.integrations.classifier.chain import ClassifierChain
from app.schemas.category import CategoryBrief
from app.schemas.scan import PredictionOut
from app.services import category_service


def classify(db: Session, user_id: int | None, texts: list[str], classifier: ClassifierChain) -> list[PredictionOut]:
    predictions = classifier.predict_many(texts, ClassificationContext(db=db, user_id=user_id))
    categories = category_service.by_key(db)
    results: list[PredictionOut] = []
    for prediction in predictions:
        category = categories.get(prediction.category_key) if prediction else None
        confidence = prediction.confidence if prediction and category else None
        results.append(
            PredictionOut(
                category_id=category.id if category else None,
                category=CategoryBrief.model_validate(category) if category else None,
                confidence_score=round(confidence, 4) if confidence is not None else None,
                confidence_percent=round(confidence * 100) if confidence is not None else None,
                prediction_source=prediction.source if category else None,
                needs_review=(
                    category is None or confidence is None or confidence < settings.LOW_CONFIDENCE_THRESHOLD
                ),
            )
        )
    return results
