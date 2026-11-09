# Deployment Baseline

Dokumen ini mendefinisikan proses dasar untuk membangun dan menjalankan STRUKKU pada environment development, testing, dan production.

## Development

```powershell
Copy-Item .env.example .env
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Pengembangan lokal boleh memakai SQLite dan Tesseract Windows.

## Testing

Gunakan konfigurasi terpisah:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

CI otomatis memakai `APP_ENV=testing` dan database in-memory. File model dan dependency tetap dari repository.

## Production dengan Docker

Build:

```bash
docker build -t strukku-backend:latest .
```

Jalankan dengan environment production:

```bash
docker run -d \
  --name strukku-backend \
  --env-file .env.production \
  -p 8000:8000 \
  -v /path/backup-strukku:/app/storage \
  strukku-backend:latest
```

`-v` saat ini dipakai sebagai baseline pengembangan. Deployment skala produksi sebaiknya menggunakan object storage pada Tahap 4.

## Checklist sebelum deployment

- `.env.production` berisi credential baru, bukan placeholder.
- `JWT_SECRET_KEY` acak.
- `APP_ENV=production`.
- `CORS_ORIGINS` hanya berisi domain resmi.
- Database produksi menggunakan PostgreSQL.
- Backup database tersedia dan proses restore sudah diuji.
- Tesseract serta bahasa `ind` dan `eng` terpasang.
- `/api/v1/health` menunjukkan seluruh komponen ready.
- `/docs` dipertimbangkan untuk dinonaktifkan atau dibatasi di produksi.
- Model ML sesuai dengan versi scikit-learn yang dipakai image.
- Test CI sudah lulus.

## Smoke test setelah deployment

1. Buka `/`.
2. Cek `/api/v1/health`.
3. Cek `/docs` bila masih diizinkan.
4. Daftar atau login akun test.
5. Buka `/api/v1/auth/me`.
6. Panggil `/api/v1/dashboard`.
7. Upload satu gambar test melalui `/api/v1/scans`.
8. Simpan scan melalui `/api/v1/receipts`.

Jika salah satu smoke test gagal, hentikan deployment atau jalankan rollback image sebelumnya.
