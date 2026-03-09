"""File/object storage abstraction. Local FS for dev, S3-compatible for cloud."""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.platform.config.settings import settings


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, path: str, data: bytes) -> str:
        ...

    @abstractmethod
    async def load(self, path: str) -> bytes:
        ...

    @abstractmethod
    async def exists(self, path: str) -> bool:
        ...

    @abstractmethod
    async def list_files(self, prefix: str) -> list[str]:
        ...

    async def save_json(self, path: str, obj: Any) -> str:
        data = json.dumps(obj, default=str, indent=2).encode()
        return await self.save(path, data)

    async def load_json(self, path: str) -> Any:
        data = await self.load(path)
        return json.loads(data)


class LocalStorage(StorageBackend):
    def __init__(self, base_path: str | None = None):
        self.base = Path(base_path or settings.storage_path)
        self.base.mkdir(parents=True, exist_ok=True)

    async def save(self, path: str, data: bytes) -> str:
        full = self.base / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)
        return str(full)

    async def load(self, path: str) -> bytes:
        full = self.base / path
        return full.read_bytes()

    async def exists(self, path: str) -> bool:
        return (self.base / path).exists()

    async def list_files(self, prefix: str) -> list[str]:
        target = self.base / prefix
        if not target.exists():
            return []
        return [str(p.relative_to(self.base)) for p in target.rglob("*") if p.is_file()]


def get_storage() -> StorageBackend:
    """Factory for storage backend based on settings."""
    if settings.storage_backend == "s3":
        # TODO: Implement S3Storage for cloud deployment
        raise NotImplementedError("S3 storage not yet implemented")
    return LocalStorage()
