from __future__ import annotations

from nova_backend.config import DATA_DIR, UPLOADS_DIR


def test_default_uploads_live_under_the_configured_data_store():
    assert UPLOADS_DIR == DATA_DIR / "uploads"
