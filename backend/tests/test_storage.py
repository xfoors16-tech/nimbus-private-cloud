from pathlib import Path
import sys
from types import SimpleNamespace

from app.storage import ObjectStorage


def test_local_storage_does_not_require_s3_dependencies(monkeypatch):
    monkeypatch.setattr(sys, "modules", {**sys.modules, "boto3": None})
    local_storage = ObjectStorage()

    assert local_storage.client is None


def test_local_storage_creates_nested_object_directories(tmp_path: Path):
    local_storage = ObjectStorage.__new__(ObjectStorage)
    local_storage.settings = SimpleNamespace(storage_root=tmp_path)
    local_storage.client = None

    local_storage.put("avatars/profile.png", b"image-data", "image/png")

    assert (tmp_path / "avatars" / "profile.png").read_bytes() == b"image-data"
    assert b"".join(local_storage.stream("avatars/profile.png", chunk_size=3)) == b"image-data"
    local_storage.delete("avatars/profile.png")
    assert not (tmp_path / "avatars" / "profile.png").exists()
