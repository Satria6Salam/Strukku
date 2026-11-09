"""Kategori pengeluaran: sinkronisasi katalog dan validasi ID."""
import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BadRequestError
from app.models import Category

logger = logging.getLogger("strukku")


def load_catalog() -> list[dict]:
    path = settings.path(settings.CATEGORY_CATALOG_PATH)
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("categories", [])
    except (OSError, ValueError) as exc:
        logger.error("Gagal membaca katalog kategori %s: %s", path, exc)
        return []


def sync_categories(db: Session, model_classes: list[str]) -> None:
    """Samakan tabel categories dengan katalog + label model ML.

    - Kategori di katalog dibuat/diperbarui dan diaktifkan.
    - Label model yang belum ada di katalog tetap dibuat (nama dari label).
    - Kategori lama yang tidak lagi dipakai dinonaktifkan, BUKAN dihapus,
      agar transaksi lama tetap utuh.
    """
    catalog = load_catalog()
    wanted: dict[str, dict] = {}
    for order, entry in enumerate(catalog):
        wanted[entry["key"]] = {**entry, "sort_order": order}
    for label in model_classes:
        if label not in wanted:
            logger.warning("Label model '%s' belum ada di category_catalog.json", label)
            wanted[label] = {"key": label, "display_name": label.replace("_", " "), "sort_order": len(wanted)}

    existing = {c.name: c for c in db.scalars(select(Category))}
    for key, entry in wanted.items():
        category = existing.get(key) or Category(name=key)
        category.display_name = entry.get("display_name") or key.replace("_", " ")
        category.description = entry.get("description", category.description)
        category.icon = entry.get("icon")
        category.color = entry.get("color")
        category.sort_order = entry["sort_order"]
        category.is_active = True
        db.add(category)
    for key, category in existing.items():
        if key not in wanted and category.is_active:
            category.is_active = False
    db.commit()


def list_active(db: Session) -> list[Category]:
    return list(
        db.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order, Category.id))
    )


def by_key(db: Session) -> dict[str, Category]:
    return {c.name: c for c in db.scalars(select(Category))}


def validate_ids(db: Session, ids: set[int | None]) -> dict[int, Category]:
    wanted = {i for i in ids if i is not None}
    if not wanted:
        return {}
    found = {c.id: c for c in db.scalars(select(Category).where(Category.id.in_(wanted)))}
    missing = sorted(wanted - found.keys())
    if missing:
        raise BadRequestError(
            f"Kategori dengan ID {', '.join(map(str, missing))} tidak ditemukan.", code="CATEGORY_NOT_FOUND"
        )
    return found
