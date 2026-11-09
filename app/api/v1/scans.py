from fastapi import APIRouter, File, Response, UploadFile
from sqlalchemy import select

from app.api.deps import DB, OCR, Classifier, CurrentUser, Parser, Storage
from app.core.exceptions import NotFoundError
from app.schemas.scan import ClassifyItemOut, ClassifyRequest, ScanOut
from app.services import prediction_service, scan_service
from app.models import ScanAsset
from app.core.timeutils import utcnow

router = APIRouter(tags=["Pindai & Klasifikasi"])


@router.post("/scans", response_model=ScanOut)
def scan_receipt(
    db: DB,
    user: CurrentUser,
    ocr: OCR,
    parser: Parser,
    classifier: Classifier,
    storage: Storage,
    file: UploadFile = File(..., description="Foto struk (JPG/PNG/WEBP)"),
):
    """Pindai foto struk: OCR → parsing → prediksi kategori per barang.

    Data **belum** disimpan. Tampilkan hasilnya di layar Koreksi & Validasi,
    lalu kirim ke `POST /receipts` beserta `scan_id`.
    """
    content = file.file.read()
    return scan_service.scan_receipt(db, user, content, ocr, parser, classifier, storage)


@router.get(
    "/scans/{scan_id}/image",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}}},
)
def scan_image(scan_id: str, db: DB, user: CurrentUser, storage: Storage):
    """Gambar hasil scan (untuk tombol "Lihat struk penuh" sebelum disimpan)."""
    if not storage.is_valid_key(scan_id):
        raise NotFoundError("Gambar scan tidak ditemukan.", code="IMAGE_NOT_FOUND")
    asset = db.scalar(select(ScanAsset).where(
        ScanAsset.owner_id == user.id,
        ScanAsset.storage_key == scan_id,
        ScanAsset.deleted_at.is_(None),
        ScanAsset.expires_at > utcnow(),
    ))
    data = storage.read(user.id, scan_id) if asset is not None else None
    if data is None:
        raise NotFoundError("Gambar scan tidak ditemukan.", code="IMAGE_NOT_FOUND")
    return Response(content=data, media_type="image/jpeg")


@router.post("/classify", response_model=list[ClassifyItemOut])
def classify_items(data: ClassifyRequest, db: DB, user: CurrentUser, classifier: Classifier):
    """Prediksi kategori untuk nama barang yang diketik manual."""
    texts = [t.strip() for t in data.texts]
    predictions = prediction_service.classify(db, user.id, texts, classifier)
    return [ClassifyItemOut(text=t, **p.model_dump()) for t, p in zip(texts, predictions)]
