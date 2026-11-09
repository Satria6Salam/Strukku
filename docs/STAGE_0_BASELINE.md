# Tahap 0: Baseline dan Dokumentasi Teknis

Dokumen ini menjadi acuan awal sebelum fitur produksi tambahan dikembangkan.

## Status baseline

- Test date: 2026-11-06
- Result: 22 tests passed, 2 warnings
- Python local: 3.13 x64
- OS local: Windows
- Test command: `.venv\Scripts\python.exe -m pytest -q`
- CI Python: 3.12 on Ubuntu

## Lingkungan

| Environment | Tujuan | Database | Konfigurasi |
|---|---|---|---|
| Development | Pengembangan dan demo lokal | SQLite | `.env.example` atau `.env` |
| Testing | Pengujian lokal/CI | SQLite temporary atau memory | `.env.testing.example` |
| Production | Layanan user/hosting | PostgreSQL/Supabase | `.env.production.example` atau secret manager |

### Aturan environment

- Jangan commit `.env` atau credential nyata.
- `APP_ENV=production` hanya boleh dipakai di server produksi.
- Secret production wajib disediakan melalui environment variable atau secret manager.
- Jangan gunakan secret default bila menjalankan produksi.
- Testing harus memakai database dan folder upload yang terisolasi.

## Versi runtime baseline

Versi dependency produksi ada di `requirements.txt`.

| Komponen | Versi |
|---|---|
| Python target | 3.11–3.13 |
| Python CI | 3.12 |
| FastAPI | 0.120.0 |
| Uvicorn | 0.38.0 |
| SQLAlchemy | 2.0.44 |
| Alembic | 1.20.1 |
| scikit-learn | 1.6.1 |
| NumPy | 2.3.4 |
| Pydantic Settings | 2.11.0 |
| Tesseract | Versi lokal/CI yang terinstal |

Untuk meningkatkan atau mengganti dependency, ubah manifest terlebih dahulu dan jalankan seluruh test sebelum merge.

## Jalankan baseline lokal

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## Contract API

- Dokumentasi Flutter: `docs/API_FRONTEND.md`
- OpenAPI generatif: `/docs`
- File OpenAPI statis: `docs/openapi.json`
- Endpoint utama:
  - `/api/v1/auth/register`
  - `/api/v1/auth/login`
  - `/api/v1/scans`
  - `/api/v1/receipts`
  - `/api/v1/dashboard`
  - `/api/v1/analytics/categories`
  - `/api/v1/analytics/monthly`
  - `/api/v1/health`

Keseluruhan endpoint yang memerlukan login harus memakai:

```text
Authorization: Bearer <access_token>
```

## CI baseline

Workflow CI ada di `.github/workflows/ci.yml`.

CI akan:

1. Checkout kode.
2. Menyiapkan Python 3.12.
3. Menginstal Tesseract, bahasa Inggris, dan bahasa Indonesia.
4. Menginstal dependency development.
5. Menjalankan seluruh `pytest`.

Tes harus lulus sebelum perubahan dikategorikan siap merge.

## Kapan database diubah

1. Ubah SQLAlchemy model di `app/models/`.
2. Jalankan Alembic autogenerate.
3. Tinjau dan selesaikan file migrasi di `alembic/versions/`.
4. Uji migrasi pada database development dan snapshot database lama.
5. Jalankan backup sebelum migrasi produksi.
6. Jalankan migrasi dan smoke test.

Perubahan database memerlukan migrasi baru. Jangan menghapus tabel lama sebagai bagian migrasi otomatis karena data lama dan pengguna produksi dapat hilang.

## Kapan model diubah

Update model hanya jika seluruh langkah berikut selesai:

1. Data training dan koreksi diekspor.
2. Dataset dibersihkan dan dibagi untuk evaluasi.
3. Model dibuat oleh scikit-learn kompatibel `1.6.1`.
4. Akurasi dan kebutuhan review dievaluasi.
5. File `.joblib` baru ditempatkan pada direktori model dan dicatat versinya.
6. `MODEL_PATH` diperbarui pada konfigurasi target.
7. `/api/v1/health` memastikan model siap dan kelas kategori sesuai.
8. Pengujian klasifikasi dan scan dijalankan ulang.

Jika model baru gagal pada pengujian regresi, kembalikan `MODEL_PATH` ke model versi sebelumnya.
