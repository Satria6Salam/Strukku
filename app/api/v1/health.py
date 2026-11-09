from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DB
from app.core.config import settings
from app.integrations.providers import get_classifier, get_ocr_engine

router = APIRouter(tags=["Health"])


@router.get("/health")
def health(db: DB):
    """Status server, database, model ML, dan OCR. Cek ini dulu bila ada masalah."""
    try:
        db.execute(text("SELECT 1"))
        database = {"ready": True, "engine": db.get_bind().dialect.name}
        if not settings.is_sqlite:
            pool = db.get_bind().pool
            database.update({
                "pool_size": getattr(pool, "size", lambda: None)() if callable(getattr(pool, "size", None)) else getattr(pool, "size", None),
                "checked_out_connections": getattr(pool, "checkedout", lambda: None)() if callable(getattr(pool, "checkedout", None)) else getattr(pool, "checkedout", None),
            })
    except Exception as exc:  # pragma: no cover
        database = {"ready": False, "message": str(exc)}
    try:
        ocr = get_ocr_engine().status()
    except Exception as exc:  # pragma: no cover
        ocr = {"ready": False, "message": str(exc)}
    classifiers = get_classifier().status()
    ok = database["ready"] and ocr.get("ready") and all(c.get("ready") for c in classifiers)
    return {
        "status": "ok" if ok else "degraded",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "database": database,
        "ocr": ocr,
        "classifiers": classifiers,
        "low_confidence_threshold": settings.LOW_CONFIDENCE_THRESHOLD,
    }
