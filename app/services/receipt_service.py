"""Pencatatan transaksi (struk) milik pengguna yang sedang login."""
import math
from collections import defaultdict
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.timeutils import local_now, utcnow
from app.integrations.storage.base import StorageBackend
from app.models import Receipt, ReceiptItem, ScanAsset, User
from app.schemas.category import CategoryBrief
from app.schemas.common import Page
from app.schemas.receipt import (
    ReceiptCreate,
    ReceiptItemIn,
    ReceiptItemOut,
    ReceiptItemUpdate,
    ReceiptOut,
    ReceiptSummaryOut,
    ReceiptUpdate,
)
from app.services import category_service

_ITEMS = selectinload(Receipt.items).joinedload(ReceiptItem.category)


# ------------------------------------------------------------ serializers
def image_url(receipt: Receipt) -> str | None:
    return f"{settings.API_PREFIX}/receipts/{receipt.id}/image" if receipt.image_key else None


def _main_category(receipt: Receipt) -> CategoryBrief | None:
    totals: dict[int, float] = defaultdict(float)
    lookup = {}
    for item in receipt.items:
        if item.category is not None:
            totals[item.category_id] += float(item.item_price or 0)
            lookup[item.category_id] = item.category
    if not totals:
        return None
    best = max(totals, key=totals.get)
    return CategoryBrief.model_validate(lookup[best])


def to_summary(receipt: Receipt) -> ReceiptSummaryOut:
    return ReceiptSummaryOut(
        id=receipt.id,
        merchant_name=receipt.merchant_name,
        transaction_date=receipt.transaction_date,
        total_amount=float(receipt.total_amount) if receipt.total_amount is not None else None,
        item_count=len(receipt.items),
        image_url=image_url(receipt),
        main_category=_main_category(receipt),
        created_at=receipt.created_at,
    )


def to_detail(receipt: Receipt) -> ReceiptOut:
    summary = to_summary(receipt)
    return ReceiptOut(
        **summary.model_dump(),
        items_total=round(sum(float(i.item_price or 0) for i in receipt.items), 2),
        updated_at=receipt.updated_at,
        items=[ReceiptItemOut.model_validate(i) for i in receipt.items],
    )


# ---------------------------------------------------------------- helpers
def _get_owned(db: Session, user: User, receipt_id: int) -> Receipt:
    receipt = db.scalar(
        select(Receipt).options(_ITEMS).where(Receipt.id == receipt_id, Receipt.user_id == user.id)
    )
    if receipt is None:
        raise NotFoundError("Struk tidak ditemukan.", code="RECEIPT_NOT_FOUND")
    return receipt


def _build_items(db: Session, items: list[ReceiptItemIn]) -> list[ReceiptItem]:
    ids = {i.category_id for i in items} | {i.predicted_category_id for i in items}
    category_service.validate_ids(db, ids)
    rows = []
    for item in items:
        corrected = item.is_user_corrected
        if corrected is None:
            corrected = item.category_id is not None and item.category_id != item.predicted_category_id
        rows.append(
            ReceiptItem(
                item_name=item.item_name,
                quantity=item.quantity,
                item_price=item.item_price,
                category_id=item.category_id,
                predicted_category_id=item.predicted_category_id,
                prediction_source=item.prediction_source,
                confidence_score=item.confidence_score,
                is_user_corrected=corrected,
            )
        )
    return rows


def _total(data_total: float | None, items: list[ReceiptItemIn]) -> float:
    if data_total is not None:
        return data_total
    return round(sum(i.item_price or 0 for i in items), 2)


# --------------------------------------------------------------- commands
def create(db: Session, user: User, data: ReceiptCreate, storage: StorageBackend) -> ReceiptOut:
    image_key = None
    if data.scan_id:
        if not storage.is_valid_key(data.scan_id) or not storage.exists(user.id, data.scan_id):
            raise BadRequestError("scan_id tidak valid atau gambarnya tidak ditemukan.", code="INVALID_SCAN_ID")
        if db.scalar(select(Receipt.id).where(Receipt.image_key == data.scan_id)) is not None:
            raise ConflictError("Struk dari hasil scan ini sudah disimpan.", code="SCAN_ALREADY_SAVED")
        scan_asset = db.scalar(
            select(ScanAsset).where(
                ScanAsset.storage_key == data.scan_id,
                ScanAsset.owner_id == user.id,
                ScanAsset.deleted_at.is_(None),
                ScanAsset.used_at.is_(None),
                ScanAsset.expires_at > utcnow(),
            )
        )
        if scan_asset is None:
            raise BadRequestError("scan_id tidak valid untuk pengguna ini.", code="INVALID_SCAN_OWNER")
        image_key = data.scan_id

    receipt = Receipt(
        user_id=user.id,
        merchant_name=(data.merchant_name or "").strip() or None,
        transaction_date=data.transaction_date or local_now(),
        total_amount=_total(data.total_amount, data.items),
        image_key=image_key,
        raw_text=data.raw_text,
        items=_build_items(db, data.items),
    )
    db.add(receipt)
    if image_key:
        scan_asset = db.scalar(select(ScanAsset).where(ScanAsset.storage_key == image_key, ScanAsset.owner_id == user.id))
        if scan_asset:
            scan_asset.used_at = utcnow()
    db.commit()
    return to_detail(_get_owned(db, user, receipt.id))


def update(db: Session, user: User, receipt_id: int, data: ReceiptUpdate) -> ReceiptOut:
    receipt = _get_owned(db, user, receipt_id)
    new_items = _build_items(db, data.items)
    receipt.merchant_name = (data.merchant_name or "").strip() or None
    receipt.transaction_date = data.transaction_date or receipt.transaction_date or local_now()
    receipt.total_amount = _total(data.total_amount, data.items)
    receipt.items.clear()
    receipt.items.extend(new_items)
    db.commit()
    db.expire_all()
    return to_detail(_get_owned(db, user, receipt_id))


def update_item(db: Session, user: User, receipt_id: int, item_id: int, data: ReceiptItemUpdate) -> ReceiptOut:
    receipt = _get_owned(db, user, receipt_id)
    item = next((i for i in receipt.items if i.id == item_id), None)
    if item is None:
        raise NotFoundError("Barang tidak ditemukan pada struk ini.", code="ITEM_NOT_FOUND")
    changes = data.model_dump(exclude_unset=True)
    if "category_id" in changes:
        category_service.validate_ids(db, {changes["category_id"]})
        item.category_id = changes["category_id"]
        item.is_user_corrected = item.category_id is not None and item.category_id != item.predicted_category_id
    for field in ("item_name", "quantity", "item_price"):
        if changes.get(field) is not None:
            setattr(item, field, " ".join(changes[field].split()) if field == "item_name" else changes[field])
    db.commit()
    db.expire_all()
    return to_detail(_get_owned(db, user, receipt_id))


def delete(db: Session, user: User, receipt_id: int, storage: StorageBackend) -> None:
    receipt = _get_owned(db, user, receipt_id)
    image_key = receipt.image_key
    db.delete(receipt)
    db.commit()
    if image_key:
        storage.delete(user.id, image_key)
        asset = db.scalar(select(ScanAsset).where(ScanAsset.storage_key == image_key, ScanAsset.owner_id == user.id))
        if asset:
            from app.core.timeutils import utcnow
            asset.deleted_at = utcnow()
            db.commit()


# ---------------------------------------------------------------- queries
def get(db: Session, user: User, receipt_id: int) -> ReceiptOut:
    return to_detail(_get_owned(db, user, receipt_id))


def get_image(db: Session, user: User, receipt_id: int, storage: StorageBackend) -> bytes:
    receipt = _get_owned(db, user, receipt_id)
    data = storage.read(user.id, receipt.image_key) if receipt.image_key else None
    if data is None:
        raise NotFoundError("Struk ini tidak memiliki gambar.", code="IMAGE_NOT_FOUND")
    return data


def list_receipts(
    db: Session,
    user: User,
    *,
    page: int = 1,
    page_size: int = 20,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    category_id: int | None = None,
    search: str | None = None,
) -> Page[ReceiptSummaryOut]:
    conditions = [Receipt.user_id == user.id]
    if date_from:
        conditions.append(Receipt.transaction_date >= date_from)
    if date_to:
        conditions.append(Receipt.transaction_date < date_to)
    if category_id:
        conditions.append(Receipt.items.any(ReceiptItem.category_id == category_id))
    if search:
        pattern = f"%{search.strip().lower()}%"
        conditions.append(
            or_(
                func.lower(Receipt.merchant_name).like(pattern),
                Receipt.items.any(func.lower(ReceiptItem.item_name).like(pattern)),
            )
        )

    total = db.scalar(select(func.count(Receipt.id)).where(*conditions)) or 0
    rows = db.scalars(
        select(Receipt)
        .options(_ITEMS)
        .where(*conditions)
        .order_by(Receipt.transaction_date.desc(), Receipt.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page[ReceiptSummaryOut](
        items=[to_summary(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )
