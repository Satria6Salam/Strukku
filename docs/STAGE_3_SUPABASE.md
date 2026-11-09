# Tahap 3 - Migrasi Database Produksi

## 1. Supabase connection string

Gunakan connection string mode **Session pooler** dari Supabase Dashboard:

```text
postgresql+psycopg://postgres.PROJECT_REF:PASSWORD@HOST:5432/postgres?sslmode=require
```

Isi password khusus dari URL encoding (`@` menjadi `%40`, `#` menjadi `%23`, dan sebagainya). Jangan commit kredensial.

Atur konfigurasi:

```env
DATABASE_URL=postgresql+psycopg://...
AUTO_MIGRATE=true
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT_SECONDS=30
DB_POOL_RECYCLE_SECONDS=1800
```

## 2. Migrasi staging

1. Buat database/project staging Supabase terpisah.
2. Set `DATABASE_URL` staging.
3. Jalankan:

```powershell
.\.venv\Scripts\python.exe -m app.db.migrate
```

4. Uji health, autentikasi, receipt, analitik, dan refresh token.

## 3. Copy data SQLite ke staging

Pastikan skema staging sudah mencapai revisi terbaru.

```powershell
$target = "postgresql+psycopg://..."
.\.venv\Scripts\python.exe scripts/migrate_sqlite_to_postgres.py --source "sqlite:///./strukku.db" --target $target
```

Gunakan database staging kosong atau pertimbangkan `--truncate` setelah backup.

## 4. Backup

Aktifkan backup otomatis/PITR pada Supabase Dashboard. Untuk backup manual:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://..."
.\scripts\backup_database.ps1 -DatabaseUrl $env:DATABASE_URL
```

Untuk jadwal Windows Task Scheduler, panggil skrip PowerShell ini secara berkala dan simpan output dump di penyimpanan aman.

## 5. Restore staging

```powershell
$env:STAGING_DATABASE_URL = "postgresql+psycopg://...staging..."
.\scripts\restore_database.ps1 -BackupFile ".\storage\backups\strukku-YYYYMMDD-HHmmss.dump" -StagingDatabaseUrl $env:STAGING_DATABASE_URL
```

Setelah restore, jalankan migration, health check, login test, data count check, dan satu alur upload transaksi.

## 6. Indeks dan foreign key

Skema mencakup:

- `users.email`
- `receipts(user_id, transaction_date)`
- `receipts(transaction_date)`
- `receipt_items(receipt_id, category_id)`
- foreign key receipt, item, kategori, dan user

## Aturan environment database

- `APP_ENV=production`: hanya PostgreSQL/Supabase; SQLite menyebabkan konfigurasi ditolak.
- `APP_ENV=testing`: SQLite in-memory atau file SQLite sementara diperbolehkan.
- Pengembangan lokal dapat memakai SQLite sementara.
- Container produksi tidak memakai SQLite atau volume SQLite.
- Volume container hanya boleh dipakai untuk media/file upload, bukan database aplikasi.
