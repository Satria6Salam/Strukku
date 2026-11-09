from datetime import date, datetime, time

from fastapi import APIRouter, Query, Response, status

from app.api.deps import DB, CurrentUser, Storage
from app.core.exceptions import BadRequestError
from app.core.timeutils import month_range, parse_month
from app.schemas.common import Page
from app.schemas.receipt import ReceiptCreate, ReceiptItemUpdate, ReceiptOut, ReceiptSummaryOut, ReceiptUpdate
from app.services import receipt_service

router = APIRouter(prefix="/receipts", tags=["Struk / Transaksi"])


@router.post("", response_model=ReceiptOut, status_code=status.HTTP_201_CREATED)
def create_receipt(data: ReceiptCreate, db: DB, user: CurrentUser, storage: Storage):
    """Simpan struk setelah divalidasi pengguna (tombol **Save Data**)."""
    return receipt_service.create(db, user, data, storage)


@router.get("", response_model=Page[ReceiptSummaryOut])
def list_receipts(
    db: DB,
    user: CurrentUser,
    month: str | None = Query(None, description="Filter bulan YYYY-MM, mis. 2026-10", examples=["2026-10"]),
    date_from: date | None = Query(None, description="Tanggal awal (inklusif)"),
    date_to: date | None = Query(None, description="Tanggal akhir (inklusif)"),
    category_id: int | None = Query(None, description="Struk yang memuat barang kategori ini"),
    q: str | None = Query(None, max_length=100, description="Cari nama toko / nama barang"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Riwayat struk terbaru lebih dulu, dengan filter & paginasi."""
    start = end = None
    if month:
        start, end = month_range(parse_month(month))
    if date_from:
        start = datetime.combine(date_from, time.min)
    if date_to:
        end = datetime.combine(date_to, time.max)
    if start and end and start > end:
        raise BadRequestError("date_from tidak boleh setelah date_to.", code="INVALID_DATE_RANGE")
    return receipt_service.list_receipts(
        db, user, page=page, page_size=page_size, date_from=start, date_to=end, category_id=category_id, search=q
    )


@router.get("/{receipt_id}", response_model=ReceiptOut)
def get_receipt(receipt_id: int, db: DB, user: CurrentUser):
    return receipt_service.get(db, user, receipt_id)


@router.put("/{receipt_id}", response_model=ReceiptOut)
def update_receipt(receipt_id: int, data: ReceiptUpdate, db: DB, user: CurrentUser):
    """Ganti seluruh isi struk (header + daftar barang)."""
    return receipt_service.update(db, user, receipt_id, data)


@router.patch("/{receipt_id}/items/{item_id}", response_model=ReceiptOut)
def update_receipt_item(receipt_id: int, item_id: int, data: ReceiptItemUpdate, db: DB, user: CurrentUser):
    """Ubah satu barang, mis. koreksi kategori setelah struk tersimpan."""
    return receipt_service.update_item(db, user, receipt_id, item_id, data)


@router.delete("/{receipt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_receipt(receipt_id: int, db: DB, user: CurrentUser, storage: Storage):
    receipt_service.delete(db, user, receipt_id, storage)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{receipt_id}/image", response_class=Response, responses={200: {"content": {"image/jpeg": {}}}})
def get_receipt_image(receipt_id: int, db: DB, user: CurrentUser, storage: Storage):
    """Foto struk. Butuh header `Authorization: Bearer <token>`."""
    return Response(content=receipt_service.get_image(db, user, receipt_id, storage), media_type="image/jpeg")
