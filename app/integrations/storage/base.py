import re
from abc import ABC, abstractmethod

KEY_PATTERN = re.compile(r"^[0-9a-f]{32}\.jpg$")


class StorageBackend(ABC):
    """Kontrak penyimpanan gambar struk.

    Setiap file dimiliki satu pengguna (`owner_id`), sehingga pengguna lain
    tidak bisa mengakses gambar walau mengetahui kuncinya. Untuk pindah ke
    Supabase Storage/S3 cukup buat kelas turunan baru dan daftarkan di
    `app/integrations/providers.py`.
    """

    name = "base"

    @staticmethod
    def is_valid_key(key: str) -> bool:
        return bool(KEY_PATTERN.match(key or ""))

    @abstractmethod
    def save(self, owner_id: int, data: bytes) -> str:
        """Simpan JPEG, kembalikan kunci file."""

    @abstractmethod
    def read(self, owner_id: int, key: str) -> bytes | None:
        ...

    @abstractmethod
    def exists(self, owner_id: int, key: str) -> bool:
        ...

    @abstractmethod
    def delete(self, owner_id: int, key: str) -> None:
        ...

    def signed_url(self, owner_id: int, key: str) -> str | None:
        return None
