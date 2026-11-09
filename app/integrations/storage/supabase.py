import httpx

from app.integrations.storage.base import StorageBackend


class SupabaseStorage(StorageBackend):
    name = "supabase"

    def __init__(self, url: str, service_role_key: str, bucket: str, signed_url_expiry: int = 300):
        if not url or not service_role_key:
            raise ValueError("SUPABASE_URL dan SUPABASE_SERVICE_ROLE_KEY wajib diset untuk STORAGE_BACKEND=supabase")
        self.base_url = url.rstrip("/")
        self.service_role_key = service_role_key
        self.bucket = bucket.strip("/")
        self.signed_url_expiry = signed_url_expiry

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
        }

    def _object_path(self, owner_id: int, key: str) -> str | None:
        if not self.is_valid_key(key):
            return None
        return f"{int(owner_id)}/{key}"

    def save(self, owner_id: int, data: bytes) -> str:
        from uuid import uuid4

        key = f"{uuid4().hex}.jpg"
        object_path = self._object_path(owner_id, key)
        url = f"{self.base_url}/storage/v1/object/{self.bucket}/{object_path}"
        with httpx.Client(timeout=30) as client:
            response = client.post(
                url,
                headers={**self._headers(), "Content-Type": "image/jpeg", "x-upsert": "false"},
                content=data,
            )
            response.raise_for_status()
        return key

    def read(self, owner_id: int, key: str) -> bytes | None:
        object_path = self._object_path(owner_id, key)
        if object_path is None:
            return None
        url = f"{self.base_url}/storage/v1/object/authenticated/{self.bucket}/{object_path}"
        with httpx.Client(timeout=30) as client:
            response = client.get(url, headers=self._headers())
            if response.status_code in (404, 401, 403):
                return None
            response.raise_for_status()
            return response.content

    def exists(self, owner_id: int, key: str) -> bool:
        return self.read(owner_id, key) is not None

    def delete(self, owner_id: int, key: str) -> None:
        object_path = self._object_path(owner_id, key)
        if object_path is None:
            return
        url = f"{self.base_url}/storage/v1/object/{self.bucket}"
        with httpx.Client(timeout=30) as client:
            response = client.delete(
                url,
                headers={**self._headers(), "Content-Type": "application/json"},
                json={"prefixes": [object_path]},
            )
            response.raise_for_status()

    def signed_url(self, owner_id: int, key: str) -> str | None:
        object_path = self._object_path(owner_id, key)
        if object_path is None:
            return None
        url = f"{self.base_url}/storage/v1/object/sign/{self.bucket}"
        with httpx.Client(timeout=30) as client:
            response = client.post(
                url,
                headers={**self._headers(), "Content-Type": "application/json"},
                json={"expiresIn": self.signed_url_expiry, "paths": [object_path]},
            )
            if response.status_code >= 400:
                return None
            paths = response.json()
            if not paths:
                return None
            signed_path = paths[0].get("signedURL") if isinstance(paths[0], dict) else None
            if not signed_path:
                return None
            if signed_path.startswith("http"):
                return signed_path
            return f"{self.base_url}/storage/v1{signed_path}"
