# STRUKKU Backend API v2

Backend aplikasi STRUKKU: **login/registrasi**, **pindai struk (OCR)**, **prediksi kategori barang** (riwayat koreksi pengguna → aturan kata kunci → model TF-IDF + Multinomial Naive Bayes), **pencatatan transaksi**, serta **dashboard & analitik bulanan**.

Dokumen ini adalah panduan menjalankan. Kontrak endpoint lengkap untuk tim Flutter ada di [`docs/API_FRONTEND.md`](docs/API_FRONTEND.md).

---

## Daftar isi

1. [Yang berubah dari versi sebelumnya](#1-yang-berubah-dari-versi-sebelumnya)
2. [Struktur folder & arsitektur](#2-struktur-folder--arsitektur)
3. [Persiapan (sekali saja)](#3-persiapan-sekali-saja)
4. [Instalasi & menjalankan server](#4-instalasi--menjalankan-server)
5. [Mengatur `.env` (SQLite atau Supabase)](#5-mengatur-env-sqlite-atau-supabase)
6. [Mencoba API lewat Swagger](#6-mencoba-api-lewat-swagger)
7. [Menghubungkan ke aplikasi Flutter](#7-menghubungkan-ke-aplikasi-flutter)
8. [Menjalankan pengujian otomatis](#8-menjalankan-pengujian-otomatis)
9. [Cara menambah / mengubah fitur](#9-cara-menambah--mengubah-fitur)
10. [Deploy ke server (Docker)](#10-deploy-ke-server-docker)
11. [Troubleshooting](#11-troubleshooting)
12. [Keamanan kredensial](#12-keamanan-kredensial)

---

## 1. Yang berubah dari versi sebelumnya

| Masalah di versi lama | Perbaikan di v2 |
|---|---|
| Tidak ada login; `user_id` dikirim bebas oleh klien | Register/Login dengan JWT; semua data struk terikat ke pengguna yang login, pengguna lain tidak bisa mengakses |
| Tidak ada data untuk Beranda & halaman Kategori | `GET /dashboard`, `GET /analytics/categories`, `GET /analytics/monthly` |
| Struk tidak bisa diubah/dihapus, tanpa filter/paginasi | `PUT`, `PATCH item`, `DELETE`, filter bulan/kategori/pencarian + paginasi |
| Foto disimpan tapi tidak pernah bisa dilihat lagi | Foto dikompres, metadata GPS dibuang, bisa dibuka lewat endpoint ber-token |
| Model ML tidak mengenal kata Indonesia (*susu, sabun, teh, obat* → semua "Makanan" ±40%) | Rangkaian penentu kategori: **riwayat koreksi pengguna → kata kunci Indonesia → model ML**; barang ber-keyakinan rendah ditandai `needs_review` |
| Koreksi pengguna tidak mengubah apa pun | Koreksi diingat: barang yang sama di scan berikutnya otomatis memakai kategori koreksi; data koreksi bisa diekspor untuk melatih ulang model |
| Parser sederhana: baris "HARGA JUAL"/kembalian bisa terbaca sebagai barang, qty tidak terbaca | Parser baru: qty & harga satuan, nama dan harga di 2 baris, tanggal teks ("03 Nov 2026"), jam, berhenti di baris total |
| Foto HP miring tidak diluruskan | Rotasi EXIF diperbaiki, gambar kecil diperbesar sebelum OCR |
| `create_all` tidak bisa mengubah tabel yang sudah ada | Migrasi database dengan **Alembic** (otomatis saat start); database lama di-upgrade tanpa kehilangan data |
| Kategori disinkronkan dengan `commit` di setiap request `GET` | Sinkron sekali saat server start, dari file katalog JSON |
| OCR memblokir server (fungsi sinkron di endpoint async) | Endpoint berat berjalan di thread pool |
| Format error tidak seragam | Semua error: `{"detail": "...", "code": "KODE"}` |
| Password database Supabase tertulis di `.env` dalam zip | `.env` tidak disertakan; lihat [bagian 12](#12-keamanan-kredensial) |

---

## 2. Struktur folder & arsitektur

```text
strukku_backend/
├── app/
│   ├── main.py                  # membuat aplikasi FastAPI + proses startup
│   ├── core/                    # config (.env), keamanan (JWT/bcrypt), error, utilitas waktu
│   ├── db/                      # koneksi database & runner migrasi
│   ├── models/                  # tabel SQLAlchemy: users, categories, receipts, receipt_items
│   ├── schemas/                 # bentuk request/response (Pydantic) = kontrak dengan Flutter
│   ├── services/                # LOGIKA BISNIS (auth, scan, receipt, dashboard, kategori)
│   ├── api/
│   │   ├── deps.py              # dependency: db, user login, OCR, classifier, storage
│   │   ├── router.py            # daftar semua router
│   │   └── v1/                  # endpoint HTTP (tipis, hanya memanggil services)
│   ├── integrations/            # KOMPONEN YANG BISA DIGANTI
│   │   ├── ocr/                 #   base.py (kontrak) + tesseract.py
│   │   ├── parser/              #   base.py + regex_parser.py
│   │   ├── classifier/          #   user_history, keyword_rules, sklearn_model, chain
│   │   ├── storage/             #   base.py + local.py
│   │   └── providers.py         #   memilih implementasi berdasarkan .env
│   └── data/
│       ├── category_catalog.json   # nama tampilan, ikon, warna kategori
│       └── keyword_rules.json      # kata kunci & singkatan barang Indonesia
├── alembic/versions/            # riwayat perubahan skema database
├── models/model_tfidf_mnb_v1.joblib
├── scripts/export_training_data.py
├── tests/                       # pengujian otomatis (pytest)
├── docs/API_FRONTEND.md         # kontrak API untuk tim Flutter
├── docs/openapi.json            # spesifikasi OpenAPI (bisa diimpor ke Postman)
├── .env.example
├── requirements.txt / requirements-dev.txt
└── Dockerfile
```

Alur satu request selalu sama: **route (`api/v1`) → service (`services/`) → model/integrasi**. Route tidak berisi logika, service tidak tahu soal HTTP, dan integrasi (OCR, model, penyimpanan) hanya dipakai lewat kontraknya. Karena itu satu bagian bisa diganti tanpa mengubah bagian lain.

Alur pindai struk:

```text
Foto ─► POST /scans ─► validasi gambar ─► OCR (Tesseract) ─► parser ─► penentu kategori ─► JSON hasil scan
                                                                          │
                                         riwayat koreksi pengguna ──► kata kunci ──► model ML
Pengguna memeriksa & mengoreksi ─► POST /receipts (dengan scan_id) ─► tersimpan ─► muncul di dashboard
```

---

## 3. Persiapan (sekali saja)

### A. Python
Gunakan **Python 3.11, 3.12, atau 3.13 (64-bit)**. Saat instalasi di Windows, centang **Add Python to PATH**.

```powershell
python --version
```

### B. Tesseract OCR
**Windows**
1. Unduh installer dari https://github.com/UB-Mannheim/tesseract/wiki dan instal.
2. Saat instalasi, di bagian *Additional language data*, centang **Indonesian**.
3. Lokasi default: `C:\Program Files\Tesseract-OCR\tesseract.exe`.
4. Jika lupa mencentang Indonesian: unduh `ind.traineddata` dari https://github.com/tesseract-ocr/tessdata dan taruh di `C:\Program Files\Tesseract-OCR\tessdata\`.

**macOS**: `brew install tesseract tesseract-lang`
**Ubuntu/Debian**: `sudo apt install tesseract-ocr tesseract-ocr-ind`

Cek (buka terminal baru setelah instalasi):
```powershell
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --list-langs
```
Daftar harus memuat `eng` dan `ind`.

---

## 4. Instalasi & menjalankan server

Semua perintah dijalankan dari folder `strukku_backend`.

```powershell
cd path\ke\strukku_backend

# 1. Buat & aktifkan virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1
#   macOS/Linux: source .venv/bin/activate
#   Jika PowerShell menolak: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 2. Instal dependensi
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3. Buat file konfigurasi
Copy-Item .env.example .env
#   macOS/Linux: cp .env.example .env
#   Buka .env, ganti JWT_SECRET_KEY (lihat bagian 5)

# 4. Jalankan server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Saat start, server otomatis: membuat/meng-upgrade tabel database, memuat model ML, dan menyinkronkan 6 kategori. Log terakhir yang muncul: `STRUKKU siap. Dokumentasi API: /docs`.

Buka di browser:
- Dokumentasi interaktif (Swagger): http://127.0.0.1:8000/docs
- Status sistem: http://127.0.0.1:8000/api/v1/health → semua bagian harus `"ready": true` dan `"status": "ok"`.

> `--host 0.0.0.0` diperlukan agar HP di jaringan Wi-Fi yang sama bisa mengakses server. Untuk akses dari laptop sendiri saja, boleh dihapus.

---

## 5. Mengatur `.env` (SQLite atau Supabase)

### Database
**SQLite untuk pengujian/development lokal** — tidak perlu instalasi apa pun:
```env
DATABASE_URL=sqlite:///./strukku.db
```

**Supabase PostgreSQL**:
```env
DATABASE_URL=postgresql+psycopg://postgres.PROJECT_REF:PASSWORD_BARU@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require
```
Untuk `APP_ENV=production`, SQLite ditolak saat konfigurasi dimuat dan backend tidak akan
start. Gunakan PostgreSQL/Supabase untuk produksi. Jangan memasang SQLite sebagai volume
container atau menjadikannya penyimpanan database produksi.
Ambil URL dari Supabase Dashboard → *Project Settings* → *Database* → *Connection string* (mode *Session pooler*). Jika password mengandung karakter khusus (`@ : / # ?`), tulis dalam bentuk URL-encoded (mis. `@` → `%40`).

Database Supabase yang sudah berisi tabel dari backend versi lama **tidak perlu dihapus**: saat server start, backend mendeteksi skema lama, menandainya sebagai revisi awal, lalu menambah kolom baru. Data lama tetap ada; kategori lama (F&B, Transportasi, dll.) dinonaktifkan, tidak dihapus.

### Kunci JWT (wajib diganti)
Buat string acak:
```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```
Tempel hasilnya ke `JWT_SECRET_KEY=` di `.env`. Jika kunci diganti, semua pengguna harus login ulang.

### Pengaturan lain yang sering diubah
| Variabel | Fungsi |
|---|---|
| `TESSERACT_CMD` | Lokasi `tesseract.exe`. Kosongkan di macOS/Linux. |
| `LOW_CONFIDENCE_THRESHOLD` | Di bawah nilai ini (default `0.7` = 70%) barang ditandai "Periksa". |
| `CLASSIFIER_PIPELINE` | Urutan penentu kategori. Mis. `ml_model` saja untuk menguji model murni. |
| `OCR_PSM` | Mode segmentasi Tesseract. `4` (default) cocok untuk struk; coba `6` bila hasil kurang baik. |
| `CORS_ORIGINS` | Untuk Flutter Web di produksi, isi domain web (pisahkan dengan koma). |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Lama sesi login (default 7 hari). |

Setelah mengubah `.env`, restart server (Ctrl+C lalu jalankan ulang).

---

## 6. Mencoba API lewat Swagger

1. Buka http://127.0.0.1:8000/docs.
2. **`POST /api/v1/auth/register`** → *Try it out* → isi:
   ```json
   {"full_name": "Reza", "email": "reza@gmail.com", "password": "rahasia123"}
   ```
3. Klik tombol **Authorize** (gembok, kanan atas) → isi *username* = email, *password* → **Authorize**. Sekarang semua endpoint bergembok bisa dicoba.
4. **`POST /api/v1/scans`** → pilih foto struk → *Execute*. Perhatikan `items[].category`, `confidence_percent`, `needs_review`, dan `scan_id`.
5. **`POST /api/v1/receipts`** → kirim data hasil scan (sertakan `scan_id`). Contoh lengkap ada di `docs/API_FRONTEND.md`.
6. **`GET /api/v1/dashboard`** → ringkasan bulan ini untuk Beranda.

Untuk Postman: *Import* → pilih `docs/openapi.json`.

---

## 7. Menghubungkan ke aplikasi Flutter

**Base URL** (server dijalankan dengan `--host 0.0.0.0`):
| Perangkat | Base URL |
|---|---|
| Emulator Android | `http://10.0.2.2:8000/api/v1` |
| Simulator iOS / Flutter Web / Desktop | `http://127.0.0.1:8000/api/v1` |
| HP fisik (Wi-Fi yang sama) | `http://<IP-laptop>:8000/api/v1` — lihat IP dengan `ipconfig` (Windows) |

Catatan untuk HP fisik/emulator Android:
- Izinkan Python di Windows Firewall (muncul pop-up saat pertama dijalankan; pilih *Private network*).
- Android memblokir `http://` biasa. Tambahkan `android:usesCleartextTraffic="true"` pada tag `<application>` di `android/app/src/main/AndroidManifest.xml` (untuk pengembangan).

Setiap request selain register/login/categories/health wajib memakai header:
```
Authorization: Bearer <access_token>
```
Gambar struk juga butuh header tersebut:
```dart
Image.network('$host${receipt.imageUrl}', headers: {'Authorization': 'Bearer $token'})
```
Ringkasan endpoint per layar, contoh request/response, dan daftar kode error: **`docs/API_FRONTEND.md`**.

---

## 8. Menjalankan pengujian otomatis

```powershell
pip install -r requirements-dev.txt
pytest -q
```
Pengujian memakai database sementara dan OCR tiruan, jadi tidak menyentuh data asli dan tidak butuh Tesseract. Jalankan setiap kali selesai mengubah kode.

---

## 9. Cara menambah / mengubah fitur

| Kebutuhan | Yang diubah |
|---|---|
| **Ganti nama/ikon/warna/deskripsi kategori** | `app/data/category_catalog.json` → restart. |
| **Tambah kategori baru** (mis. Transportasi) | Latih ulang model dengan label baru, lalu tambahkan entri dengan `key` yang sama di `category_catalog.json`. Kategori yang tidak ada di model tetap bisa dipilih manual. |
| **Barang sering salah kategori** | Tambahkan kata kunci / singkatan di `app/data/keyword_rules.json` → restart. Kata kunci terpanjang menang. |
| **Pakai model ML versi baru** | Taruh file `.joblib` di `models/`, ubah `MODEL_PATH` di `.env` → restart → cek `/api/v1/health`. Model harus Pipeline sklearn (atau dict `vectorizer` + `classifier`), dibuat dengan scikit-learn 1.6.1. |
| **Data untuk melatih ulang model** | `python -m scripts.export_training_data --corrected-only -o koreksi.csv` |
| **Tambah kolom/tabel** | 1) Ubah model di `app/models/`. 2) `alembic revision --autogenerate -m "tambah kolom x"`. 3) Periksa file baru di `alembic/versions/`. 4) Restart server (migrasi berjalan otomatis) atau `alembic upgrade head`. |
| **Tambah endpoint** | Schema di `app/schemas/`, logika di `app/services/`, route di `app/api/v1/<fitur>.py`, daftarkan di `app/api/router.py`, tambah tes di `tests/`. |
| **Ganti OCR** (mis. Google Vision) | Buat kelas turunan `OCREngine` di `app/integrations/ocr/`, daftarkan di `OCR_REGISTRY` (`providers.py`), set `OCR_ENGINE` di `.env`. |
| **Simpan foto di Supabase Storage/S3** | Buat kelas turunan `StorageBackend`, daftarkan di `STORAGE_REGISTRY`, set `STORAGE_BACKEND`. |
| **Format struk toko lain belum terbaca** | Tambah pola di `app/integrations/parser/regex_parser.py` dan contoh kasusnya di `tests/test_parser.py`. |
| **Perubahan yang merusak kontrak API lama** | Buat folder `app/api/v2/` dan prefix `/api/v2` agar aplikasi versi lama tetap berjalan. |

---

## 10. Deploy ke server (Docker)

```bash
docker build -t strukku-backend .
docker run -d --name strukku -p 8000:8000 --env-file .env \
  -v $(pwd)/storage:/app/storage strukku-backend
```
Image sudah berisi Tesseract + bahasa Indonesia. Untuk produksi: set `APP_ENV=production`, `JWT_SECRET_KEY` acak, `CORS_ORIGINS` spesifik, gunakan HTTPS (mis. lewat Nginx/Caddy), dan pakai PostgreSQL. Folder `storage/` harus dipasang sebagai volume agar foto tidak hilang saat container diperbarui.

---

## 11. Troubleshooting

| Gejala | Penyebab & solusi |
|---|---|
| `/health` → `ocr.ready: false` "Tesseract tidak ditemukan" | Periksa `TESSERACT_CMD` di `.env`; pastikan file `tesseract.exe` ada. Restart terminal & server. |
| `ocr.ready: false` "Data bahasa OCR belum terpasang: ind" | Pasang `ind.traineddata` (bagian 3B). |
| `ml_model.ready: false` | File model hilang atau versi scikit-learn berbeda. Jalankan `pip install -r requirements.txt` ulang. |
| `ModuleNotFoundError: No module named 'app'` | Jalankan `uvicorn` dari folder `strukku_backend`, bukan dari dalam `app/`. |
| `ZoneInfoNotFoundError: Asia/Jakarta` | `pip install tzdata`. |
| Error koneksi Supabase / `password authentication failed` | Cek URL di `.env`, password URL-encoded, pakai host *pooler* + `sslmode=require`. |
| Flutter: `Connection refused` | Base URL salah (emulator Android pakai `10.0.2.2`), server tidak dijalankan dengan `--host 0.0.0.0`, atau firewall memblokir. |
| Flutter: `401 NOT_AUTHENTICATED` | Header `Authorization: Bearer <token>` belum dikirim. `INVALID_TOKEN` = token kedaluwarsa → login ulang. |
| Scan: `OCR_EMPTY` / barang tidak terdeteksi | Foto buram/gelap/miring/terpotong. Foto struk di permukaan rata dengan cahaya cukup, isi seluruh bingkai. |
| Total struk tidak cocok (`total_matches: false`) | Ada diskon/pajak/barang yang tidak terbaca. Pengguna mengoreksi di layar validasi. |

---

## 12. Keamanan kredensial

File `.env` di zip versi sebelumnya berisi **password database Supabase asli**. Siapa pun yang menerima zip itu bisa membuka database Anda.
1. Segera **reset password database** di Supabase Dashboard → *Project Settings* → *Database* → *Reset database password*.
2. Tulis password baru hanya di `.env` lokal masing-masing anggota tim.
3. Jangan pernah memasukkan `.env` ke Git, zip tugas, chat, atau screenshot (`.env` sudah ada di `.gitignore`). Bagikan `.env.example` saja.

---

## 13. Baseline teknis dan proses pengembangan

Tahap 0 sudah menyediakan baseline project:

- Baseline pengujian dan daftar runtime: [`docs/STAGE_0_BASELINE.md`](docs/STAGE_0_BASELINE.md)
- Proses development, testing, dan deployment: [`docs/DEPLOYMENT_STAGE_0.md`](docs/DEPLOYMENT_STAGE_0.md)
- Template konfigurasi testing: [`.env.testing.example`](.env.testing.example)
- Template konfigurasi production: [`.env.production.example`](.env.production.example)
- CI pengujian otomatis: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
