# Kontrak API STRUKKU untuk Frontend (Flutter)

Base URL: `http://<host>:8000/api/v1` · Semua body JSON kecuali upload foto (multipart).
Header untuk endpoint bertanda 🔒: `Authorization: Bearer <access_token>`.

## Peta layar → endpoint

| Layar | Endpoint |
|---|---|
| 1. Register / Login | `POST /auth/register`, `POST /auth/login` |
| 2. Beranda | `GET /dashboard?month=YYYY-MM` 🔒 (satu panggilan untuk kartu total, distribusi, struk terbaru) |
| "Lihat semua" struk | `GET /receipts?page=1&page_size=20` 🔒 |
| 3. Pindai Struk | `POST /scans` 🔒 (multipart, field `file`) |
| 4. Koreksi & Validasi | `GET /categories` (dropdown), `GET /scans/{scan_id}/image` 🔒 ("Lihat struk penuh"), `POST /receipts` 🔒 (Save Data) |
| 5. Kategori Pengeluaran | `GET /analytics/categories?month=YYYY-MM` 🔒 |
| Detail struk | `GET /receipts/{id}` 🔒, `GET /receipts/{id}/image` 🔒 |
| Edit / hapus struk | `PUT /receipts/{id}` 🔒, `PATCH /receipts/{id}/items/{item_id}` 🔒, `DELETE /receipts/{id}` 🔒 |
| Tambah barang manual | `POST /classify` 🔒 (saran kategori dari nama barang) |
| Profil | `GET /auth/me` 🔒, `PATCH /users/me` 🔒, `POST /users/me/password` 🔒 |
| Grafik tren (opsional) | `GET /analytics/monthly?months=6` 🔒 |

## Aturan umum

- **Uang**: angka Rupiah (`22500.0`). Format tampilan (`Rp22.500`) dilakukan di Flutter.
- **`transaction_date`**: waktu lokal WIB tanpa zona, mis. `"2026-10-21T14:32:00"` → `DateTime.parse()` langsung. Saat mengirim boleh tanpa zona (dianggap WIB) atau dengan zona (`toUtc().toIso8601String()`, akan diubah ke WIB).
- **`created_at` / `updated_at`**: UTC dengan akhiran `Z` → `DateTime.parse(...).toLocal()`.
- **`image_url`**: path relatif. URL lengkap = `http://<host>:8000` + `image_url`, wajib dengan header Authorization.
- **Bulan**: format `YYYY-MM`. Tanpa parameter = bulan berjalan.
- **Ikon kategori**: `icon` = nama Material Icon (`restaurant`, `local_cafe`, `home`, `spa`, `medical_services`, `more_horiz`). Buat map `String → IconData` di Flutter. `color` = hex (`#2563EB`).

## Siklus token

Login dan registrasi aktif mengembalikan dua token:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

- `access_token` berlaku 30 menit.
- `refresh_token` berlaku 7 hari.
- Simpan `refresh_token` secara aman dan jangan kirim sebagai header access token.
- Saat access token kedaluwarsa, panggil `POST /auth/refresh` dengan:

```json
{"refresh_token": "TOKEN_REFRESH_LAMA"}
```

Refresh token lama tidak dapat dipakai ulang dan diganti dengan token baru pada setiap refresh.

Logout:

```text
POST /auth/logout
Authorization: Bearer ACCESS_TOKEN
{"refresh_token": "TOKEN_REFRESH"}
```

Daftar sesi aktif:

```text
GET /auth/sessions
Authorization: Bearer ACCESS_TOKEN
```

Access token otomatis tidak berlaku lagi setelah password diubah atau password direset. Semua refresh token akun juga dicabut pada aksi tersebut.

## Format error

Semua error memakai bentuk yang sama; tampilkan `detail` ke pengguna, gunakan `code` untuk logika.
```json
{"detail": "Email atau password salah.", "code": "INVALID_CREDENTIALS"}
```
Error validasi (422) menambah `errors`:
```json
{"detail": "password: String should have at least 8 characters", "code": "VALIDATION_ERROR",
 "errors": [{"field": "password", "message": "String should have at least 8 characters"}]}
```

| HTTP | code | Arti / tindakan di aplikasi |
|---|---|---|
| 401 | `NOT_AUTHENTICATED` | Belum kirim token → ke layar login |
| 401 | `INVALID_TOKEN` | Token kedaluwarsa/tidak sah → hapus token, ke layar login |
| 401 | `INVALID_CREDENTIALS` | Email/password salah |
| 409 | `EMAIL_TAKEN` | Email sudah terdaftar |
| 400 | `INVALID_IMAGE`, `EMPTY_FILE` | File bukan gambar JPG/PNG/WEBP |
| 413 | `FILE_TOO_LARGE` | Foto > 8 MB → kompres di Flutter (`imageQuality: 85`) |
| 422 | `OCR_EMPTY` | Teks tak terbaca → minta foto ulang |
| 503 | `OCR_FAILED` | Tesseract di server bermasalah |
| 400 | `INVALID_SCAN_ID` | `scan_id` salah/milik pengguna lain |
| 409 | `SCAN_ALREADY_SAVED` | Struk dari scan ini sudah tersimpan (cegah dobel tap Save) |
| 400 | `CATEGORY_NOT_FOUND` | `category_id` tidak ada |
| 404 | `RECEIPT_NOT_FOUND`, `ITEM_NOT_FOUND`, `IMAGE_NOT_FOUND` | Data tidak ada / bukan milik pengguna |
| 400 | `INVALID_MONTH` | Format bulan bukan `YYYY-MM` |
| 422 | `VALIDATION_ERROR` | Input tidak valid; lihat `errors` |

---

## 1. Autentikasi

### `POST /auth/register`
```json
{"full_name": "Reza", "email": "reza@gmail.com", "password": "rahasia123", "password_confirmation": "rahasia123"}
```
`password` 8–64 karakter. `password_confirmation` opsional (dicek bila dikirim).

Ketika verifikasi email aktif, **201** berarti registrasi berhasil tetapi akun belum bisa login penuh:
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 604800,
  "user": {"id": 1, "email": "reza@gmail.com", "full_name": "Reza", "created_at": "2026-11-05T11:52:29.779547Z"}
}
```

Respons verifikasi aktif menggunakan `message`, `email_verification_required`, dan `user` dengan field `is_email_verified`. Jika verifikasi dinonaktifkan, register tetap mengembalikan `TokenOut` seperti sebelumnya.

### Verifikasi email
- Buka tautan verifikasi yang dikirim ke email, atau panggil `GET /auth/verify-email?token=TOKEN`.
- Kirim ulang tautan: `POST /auth/resend-verification`
```json
{"email": "reza@gmail.com"}
```
- Akun belum terverifikasi menghasilkan login **403** dengan kode `EMAIL_NOT_VERIFIED`.

### `POST /auth/login`
```json
{"email": "reza@gmail.com", "password": "rahasia123"}
```
**200** dengan bentuk `TokenOut`. Simpan `access_token` (mis. `flutter_secure_storage`).
Percobaan berlebih menghasilkan **429 Too Many Requests** dengan header `Retry-After`; kode respons `TOO_MANY_REQUESTS`.

### `POST /auth/forgot-password`
```json
{"email": "reza@gmail.com"}
```
Respons selalu bersifat aman agar email yang terdaftar tidak dapat dideteksi:
```json
{"message": "Jika email terdaftar, tautan reset password telah dikirim atau diproses."}
```

### `POST /auth/reset-password`
```json
{
  "token": "TOKEN_RESET_DARI_EMAIL",
  "new_password": "passwordbaru123",
  "new_password_confirmation": "passwordbaru123"
}
```
Token berlaku 30 menit secara default, hanya dapat digunakan sekali, dan permintaan reset baru akan membatalkan token reset lama. Token tidak valid menghasilkan **400** dengan kode `INVALID_RESET_TOKEN`.

### `POST /auth/password-strength`
Endpoint ini dipakai untuk menampilkan indikator kekuatan saat pengguna mengetik password:
```json
{"password": "S!N7mQ2x#L9"}
```
Contoh respons:
```json
{
  "score": 5,
  "level": "strong",
  "label": "Kuat",
  "is_common": false,
  "suggestions": []
}
```
Nilai `level`: `weak`, `fair`, `good`, atau `strong`. Backend tetap menolak password umum meskipun panjangnya minimal 8 karakter. Register, ganti password, dan reset password menggunakan kebijakan yang sama.

### `GET /auth/me` 🔒 → `user` · `PATCH /users/me` 🔒 `{"full_name": "...", "email": "..."}` · `POST /users/me/password` 🔒 `{"current_password": "...", "new_password": "..."}`

---

## 2. Beranda — `GET /dashboard?month=2026-10` 🔒
```json
{
  "month": "2026-10",
  "month_label": "Oktober 2026",
  "total_spent": 101900.0,
  "receipt_count": 1,
  "item_count": 5,
  "previous_month_total": 0.0,
  "change_percent": null,
  "categories": [
    {
      "category": {"id": 3, "key": "Kebutuhan_Rumah_Tangga", "name": "Kebutuhan Rumah Tangga", "icon": "home", "color": "#60A5FA"},
      "description": "Perlengkapan kebersihan dan kebutuhan rumah sehari-hari",
      "amount": 24900.0,
      "percentage": 24.4,
      "item_count": 1
    }
  ],
  "recent_receipts": [
    {
      "id": 1, "merchant_name": "INDOMARET", "transaction_date": "2026-10-21T14:32:00",
      "total_amount": 101900.0, "item_count": 5, "image_url": "/api/v1/receipts/1/image",
      "main_category": {"id": 3, "key": "Kebutuhan_Rumah_Tangga", "name": "Kebutuhan Rumah Tangga", "icon": "home", "color": "#60A5FA"},
      "created_at": "2026-11-05T11:52:30.435557Z"
    }
  ]
}
```
- Kartu biru: `total_spent`, `month_label`, `receipt_count` ("24 struk tersimpan").
- Bar distribusi: `categories` (urut nominal terbesar; semua kategori aktif selalu ada, termasuk yang 0). `percentage` dihitung dari jumlah harga barang. Entri dengan `category: null` = barang tanpa kategori.
- "Struk terbaru": `recent_receipts` (maks. 5, bulan yang dipilih). Ikon struk bisa memakai `main_category.icon`.

## 3. Kategori Pengeluaran — `GET /analytics/categories?month=2026-10` 🔒
```json
{"month": "2026-10", "month_label": "Oktober 2026", "total_amount": 101900.0, "categories": [ /* sama seperti di dashboard */ ]}
```

## 4. Pindai — `POST /scans` 🔒
Multipart, field `file`. Contoh Dart (paket `http`):
```dart
final req = http.MultipartRequest('POST', Uri.parse('$baseUrl/scans'))
  ..headers['Authorization'] = 'Bearer $token'
  ..files.add(await http.MultipartFile.fromPath('file', photo.path));
final res = await http.Response.fromStream(await req.send());
```
Proses OCR butuh beberapa detik; tampilkan loading dan pakai timeout ≥ 60 detik. Respons **200**:
```json
{
  "scan_id": "6b7299de04a249e697e7eb610578b8f3.jpg",
  "image_url": "/api/v1/scans/6b7299de04a249e697e7eb610578b8f3.jpg/image",
  "merchant_name": "INDOMARET",
  "transaction_date": "2026-10-21T14:32:00",
  "total_amount": 101900.0,
  "items_total": 101900.0,
  "total_matches": true,
  "review_count": 0,
  "items": [
    {
      "index": 0,
      "item_name": "ROTI TAWAR 500G",
      "quantity": 1,
      "unit_price": 22500.0,
      "item_price": 22500.0,
      "category_id": 1,
      "category": {"id": 1, "key": "Makanan", "name": "Makanan", "icon": "restaurant", "color": "#2563EB"},
      "predicted_category_id": 1,
      "confidence_score": 0.9,
      "confidence_percent": 90,
      "prediction_source": "keyword_rules",
      "needs_review": false
    }
  ],
  "warnings": [],
  "raw_text": "INDOMARET\n..."
}
```
Untuk layar Koreksi & Validasi:
- Isi form dari `merchant_name`, `transaction_date`, `total_amount` (semuanya bisa `null` bila tak terbaca → biarkan pengguna mengisi).
- `needs_review: true` → tampilkan kuning "⚠ `confidence_percent`% – Periksa"; `false` → "Kategori otomatis". Banner atas: "`review_count` kategori perlu diperiksa".
- `category` bisa `null` → dropdown kosong, pengguna wajib memilih.
- `warnings` → tampilkan sebagai info (total tidak cocok, tanggal tak terbaca, dll.).
- `prediction_source`: `user_history` (dari koreksi pengguna sebelumnya), `keyword_rules`, `ml_model`.
- **Data belum tersimpan** sampai `POST /receipts`.

## 5. Simpan — `POST /receipts` 🔒 (tombol Save Data)
Kirim kembali data hasil scan yang sudah diperiksa. `category_id` = pilihan akhir dropdown; `predicted_category_id`, `confidence_score`, `prediction_source` disalin apa adanya dari hasil scan.
```json
{
  "scan_id": "6b7299de04a249e697e7eb610578b8f3.jpg",
  "merchant_name": "INDOMARET",
  "transaction_date": "2026-10-21T14:32:00",
  "total_amount": 101900,
  "items": [
    {"item_name": "ROTI TAWAR 500G", "quantity": 1, "item_price": 22500, "category_id": 1,
     "predicted_category_id": 1, "confidence_score": 0.9, "prediction_source": "keyword_rules"},
    {"item_name": "VITAMIN C 10 TABLET", "quantity": 1, "item_price": 15000, "category_id": 5,
     "predicted_category_id": 6, "confidence_score": 0.62, "prediction_source": "ml_model"}
  ]
}
```
- `is_user_corrected` tidak perlu dikirim: server mengisinya `true` jika `category_id` ≠ `predicted_category_id`. Barang yang dikoreksi akan otomatis memakai kategori koreksi pada scan berikutnya.
- Tanpa `scan_id` = input manual tanpa foto. `transaction_date` kosong = sekarang; `total_amount` kosong = jumlah `item_price`.
- Minimal 1 barang. **201** → objek struk lengkap (lihat bagian 6). Setelah sukses kembali ke Beranda dan muat ulang `/dashboard`.

## 6. Riwayat & detail

### `GET /receipts` 🔒
Query: `month=2026-10`, `date_from=2026-10-01`, `date_to=2026-10-31`, `category_id=3`, `q=roti` (cari toko/barang), `page=1`, `page_size=20` (maks 100).
```json
{"items": [ /* ringkasan struk seperti recent_receipts */ ], "total": 24, "page": 1, "page_size": 20, "pages": 2}
```

### `GET /receipts/{id}` 🔒
```json
{
  "id": 1, "merchant_name": "INDOMARET", "transaction_date": "2026-10-21T14:32:00",
  "total_amount": 101900.0, "item_count": 5, "image_url": "/api/v1/receipts/1/image",
  "main_category": {"id": 3, "key": "Kebutuhan_Rumah_Tangga", "name": "Kebutuhan Rumah Tangga", "icon": "home", "color": "#60A5FA"},
  "created_at": "2026-11-05T11:52:30.435557Z", "updated_at": "2026-11-05T11:52:30.435563Z",
  "items_total": 101900.0,
  "items": [
    {"id": 1, "item_name": "ROTI TAWAR 500G", "quantity": 1, "item_price": 22500.0, "category_id": 1,
     "category": {"id": 1, "key": "Makanan", "name": "Makanan", "icon": "restaurant", "color": "#2563EB"},
     "predicted_category_id": 1, "prediction_source": "keyword_rules", "confidence_score": 0.9, "is_user_corrected": false}
  ]
}
```

### Ubah & hapus
- `PATCH /receipts/{id}/items/{item_id}` 🔒 — ubah sebagian: `{"category_id": 2}` (atau `item_name`, `quantity`, `item_price`). → struk lengkap.
- `PUT /receipts/{id}` 🔒 — ganti seluruh isi; body sama dengan `POST /receipts` tanpa `scan_id`. → struk lengkap.
- `DELETE /receipts/{id}` 🔒 → **204** tanpa body (foto ikut terhapus).

## 7. Lain-lain
- `GET /categories` — tanpa token: `[{"id":1,"key":"Makanan","name":"Makanan","icon":"restaurant","color":"#2563EB","description":"...","sort_order":0}, ...]`. Simpan `id` untuk `category_id`.
- `POST /classify` 🔒 — `{"texts": ["PEPSODENT 190G", "AQUA 600ML"]}` → daftar `{text, category_id, category, confidence_score, confidence_percent, prediction_source, needs_review}`.
- `GET /analytics/monthly?month=2026-10&months=6` 🔒 → `[{"month":"2026-05","month_label":"Mei 2026","total_spent":0.0,"receipt_count":0}, ...]` (urut lama → baru).
- `GET /health` — status server; tidak perlu dipakai di aplikasi.
## Audit keamanan

- `GET /api/v1/auth/security-events?limit=50`
- Mengembalikan riwayat keamanan milik akun yang sedang login.
- Mencakup login gagal, login sukses/perangkat baru, perubahan password/reset password, dan perubahan email.
- Batas `limit`: 1 sampai 100.
- Respons tidak menyimpan password atau access token mentah.
