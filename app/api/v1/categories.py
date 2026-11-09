from fastapi import APIRouter

from app.api.deps import DB
from app.schemas.category import CategoryOut
from app.services import category_service

router = APIRouter(tags=["Kategori"])


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: DB):
    """Kategori aktif untuk dropdown di layar koreksi (urut sesuai katalog)."""
    return category_service.list_active(db)
