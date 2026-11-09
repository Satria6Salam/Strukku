"""Konfigurasi pengujian: database SQLite sementara + OCR palsu.

Jalankan: pytest -q
"""
import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="strukku-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP / 'test.db').as_posix()}"
os.environ["UPLOAD_DIR"] = str(_TMP / "uploads")
os.environ["AUTO_MIGRATE"] = "true"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["JWT_SECRET_KEY"] = "ci-test-secret-1234567890-abcdefghijklmnopqrstuvwxyz-0123456789"
os.environ["REQUIRE_EMAIL_VERIFICATION"] = "false"

import io  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.integrations.ocr.base import OCREngine  # noqa: E402
from app.integrations.providers import get_ocr_engine  # noqa: E402
from app.main import app  # noqa: E402
from app.core.rate_limit import login_rate_limiter  # noqa: E402

SAMPLE_TEXT = """INDOMARET
JL. GAJAYANA NO 50 MALANG
21.10.2026-14:32 2.0.12 J9B1-301
ROTI TAWAR 500G 1 22.500 22.500
SUSU UHT 1L 2 9.000 18.000
VITAMIN C 10 TABLET 1 15.000 15.000
BARANG ANEH XYZ 1 5.000 5.000
TOTAL : 60.500
TUNAI : 100.000
KEMBALI : 39.500
"""


class FakeOCR(OCREngine):
    name = "fake"
    text = SAMPLE_TEXT

    def extract_text(self, image):
        return self.text


@pytest.fixture(scope="session")
def client():
    app.dependency_overrides[get_ocr_engine] = lambda: FakeOCR()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_login_limiter():
    login_rate_limiter.reset()
    yield
    login_rate_limiter.reset()


def _register(client, email):
    r = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Pengguna Uji", "email": email, "password": "S!N7mQ2x"},
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def auth(client, request):
    return _register(client, f"{request.node.name[:40]}@example.com")


@pytest.fixture
def other_auth(client, request):
    return _register(client, f"lain-{request.node.name[:35]}@example.com")


@pytest.fixture
def image_bytes():
    buffer = io.BytesIO()
    Image.new("RGB", (400, 600), "white").save(buffer, format="JPEG")
    return buffer.getvalue()
