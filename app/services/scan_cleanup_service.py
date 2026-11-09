import asyncio
import logging

from sqlalchemy import select

from app.core.timeutils import utcnow
from app.db.session import SessionLocal
from app.integrations.providers import get_storage
from app.models import ScanAsset

logger = logging.getLogger("strukku")


def cleanup_expired_scans() -> int:
    storage = get_storage()
    deleted = 0
    with SessionLocal() as db:
        assets = db.scalars(
            select(ScanAsset).where(
                ScanAsset.deleted_at.is_(None),
                ScanAsset.used_at.is_(None),
                ScanAsset.expires_at <= utcnow(),
            )
        ).all()
        for asset in assets:
            try:
                storage.delete(asset.owner_id, asset.storage_key)
            except Exception as exc:
                logger.warning("Cleanup foto scan %s gagal: %s", asset.storage_key, exc)
                continue
            asset.deleted_at = utcnow()
            deleted += 1
        db.commit()
    if deleted:
        logger.info("Cleanup foto scan kedaluwarsa: %d dihapus", deleted)
    return deleted


async def cleanup_loop(interval_seconds: int = 3600) -> None:
    cleanup_expired_scans()
    while True:
        await asyncio.sleep(interval_seconds)
        cleanup_expired_scans()
