"""Gabungan semua router API v1.

Menambah fitur baru: buat file di app/api/v1/, lalu daftarkan di sini.
Perubahan besar yang merusak kontrak lama sebaiknya dibuat di app/api/v2/
agar aplikasi Flutter versi lama tetap berjalan.
"""
from fastapi import APIRouter

from app.api.v1 import auth, categories, dashboard, health, receipts, scans

api_router = APIRouter()
for module in (health, auth, categories, scans, receipts, dashboard):
    api_router.include_router(module.router)
