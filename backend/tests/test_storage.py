from pathlib import Path

import pytest
from fastapi import UploadFile

from app.core.errors import AppError
from app.core.storage import LocalStorage


@pytest.mark.asyncio
async def test_storage_uses_opaque_key(tmp_path: Path):
    from io import BytesIO

    storage = LocalStorage(tmp_path)
    key, size = await storage.save(UploadFile(filename="report.pdf", file=BytesIO(b"hello")))
    assert size == 5
    assert key.endswith(".pdf")
    assert storage.path(key).read_bytes() == b"hello"


@pytest.mark.asyncio
async def test_storage_blocks_executable(tmp_path: Path):
    from io import BytesIO

    storage = LocalStorage(tmp_path)
    with pytest.raises(AppError) as error:
        await storage.save(UploadFile(filename="bad.exe", file=BytesIO(b"MZ")))
    assert error.value.code == "blocked_file_type"
