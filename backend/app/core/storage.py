import uuid
from pathlib import Path
from typing import Protocol

from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import AppError

BLOCKED_EXTENSIONS = {".exe", ".com", ".bat", ".cmd", ".ps1", ".sh", ".js", ".html", ".svg"}
BLOCKED_MIME_TYPES = {
    "application/x-msdownload",
    "application/x-sh",
    "application/javascript",
    "text/html",
    "image/svg+xml",
}


class FileStorage(Protocol):
    """로컬 저장소와 다음 단계의 S3 구현이 공유할 최소 계약."""

    async def save(self, upload: UploadFile) -> tuple[str, int]: ...

    def path(self, key: str) -> Path: ...


class LocalStorage:
    def __init__(self, root: Path):
        self.root = root.resolve()

    async def save(self, upload: UploadFile) -> tuple[str, int]:
        suffix = Path(upload.filename or "file").suffix.lower()
        if suffix in BLOCKED_EXTENSIONS or upload.content_type in BLOCKED_MIME_TYPES:
            raise AppError(422, "blocked_file_type", "허용되지 않는 파일 형식입니다.")
        key = f"{uuid.uuid4().hex[:2]}/{uuid.uuid4().hex}{suffix}"
        destination = (self.root / key).resolve()
        if self.root not in destination.parents:
            raise AppError(400, "invalid_path", "파일 경로가 올바르지 않습니다.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        try:
            with destination.open("xb") as output:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > settings.max_upload_bytes:
                        raise AppError(413, "file_too_large", "파일 크기 제한을 초과했습니다.")
                    output.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        return key, size

    def path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root not in path.parents or not path.is_file():
            raise AppError(404, "file_not_found", "파일을 찾을 수 없습니다.")
        return path


def build_storage() -> FileStorage:
    if settings.storage_backend == "local":
        return LocalStorage(settings.storage_root)
    raise RuntimeError("S3 저장소는 API 계약만 준비되어 있습니다.")


storage = build_storage()
