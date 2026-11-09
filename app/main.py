import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.db.session import SessionLocal
from app.integrations.providers import get_classifier, get_ml_model, get_ocr_engine
from app.services import category_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("strukku")
logging.getLogger("alembic.runtime.plugins").setLevel(logging.WARNING)


def startup() -> None:
    if settings.AUTO_MIGRATE:
        from app.db.migrate import upgrade_database

        upgrade_database()
    model = get_ml_model()
    if not model.is_ready:
        logger.warning("Model ML belum siap: %s", model.error)
    with SessionLocal() as db:
        category_service.sync_categories(db, model.classes)
    get_classifier()
    ocr_status = get_ocr_engine().status()
    if not ocr_status.get("ready"):
        logger.warning("OCR belum siap: %s", ocr_status.get("message"))
    logger.info("STRUKKU siap. Dokumentasi API: /docs")


@asynccontextmanager
async def lifespan(_: FastAPI):
    startup()
    from app.services.scan_cleanup_service import cleanup_loop
    cleanup_task = asyncio.create_task(cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Backend STRUKKU: autentikasi, pindai struk (OCR), klasifikasi kategori barang, "
            "pencatatan transaksi, dan analitik pengeluaran bulanan.\n\n"
            "Klik **Authorize** lalu login (username = email) untuk mencoba endpoint yang butuh token."
        ),
        lifespan=lifespan,
    )
    origins = settings.cors_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials="*" not in origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_PREFIX)

    @app.get("/", include_in_schema=False)
    def root():
        return {"message": "STRUKKU Backend API aktif", "docs": "/docs", "api": settings.API_PREFIX}

    return app


app = create_app()
