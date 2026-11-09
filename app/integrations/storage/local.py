from pathlib import Path
from uuid import uuid4

from app.integrations.storage.base import StorageBackend


class LocalStorage(StorageBackend):
    """Menyimpan gambar di folder lokal: <UPLOAD_DIR>/<user_id>/<kunci>.jpg"""

    name = "local"

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, owner_id: int, key: str) -> Path | None:
        if not self.is_valid_key(key):
            return None
        return self.root / str(int(owner_id)) / key

    def save(self, owner_id: int, data: bytes) -> str:
        key = f"{uuid4().hex}.jpg"
        path = self._path(owner_id, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def read(self, owner_id: int, key: str) -> bytes | None:
        path = self._path(owner_id, key)
        return path.read_bytes() if path and path.is_file() else None

    def exists(self, owner_id: int, key: str) -> bool:
        path = self._path(owner_id, key)
        return bool(path and path.is_file())

    def delete(self, owner_id: int, key: str) -> None:
        path = self._path(owner_id, key)
        if path and path.is_file():
            path.unlink()
