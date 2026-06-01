import pytest

from app.storage.assets import LocalAssetStorage


def test_local_asset_storage_writes_under_tenant_history_root(tmp_path):
    storage = LocalAssetStorage(tmp_path)

    ref = storage.put_bytes(
        tenant_id="tenant-a",
        record_id="record-1",
        relative_path="preview/final.pdf",
        data=b"pdf",
    )

    assert ref.asset_key == "history/record-1/preview/final.pdf"
    assert ref.path == tmp_path / "tenant-a" / "history" / "record-1" / "preview" / "final.pdf"
    assert ref.path.read_bytes() == b"pdf"


def test_local_asset_storage_rejects_path_traversal(tmp_path):
    storage = LocalAssetStorage(tmp_path)

    with pytest.raises(ValueError):
        storage.put_bytes(
            tenant_id="tenant-a",
            record_id="record-1",
            relative_path="../secret.txt",
            data=b"secret",
        )
