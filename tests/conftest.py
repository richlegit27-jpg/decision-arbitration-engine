# PYTEST_RESTORE_NOVA_MEMORY_LOCK
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def restore_nova_memory_file_after_test():
    memory_path = Path(r"C:\Users\Owner\nova\data\nova_memory.json")

    existed = memory_path.exists()
    original_text = memory_path.read_text(encoding="utf-8") if existed else None

    yield

    if existed:
        memory_path.write_text(original_text or "", encoding="utf-8")
    elif memory_path.exists():
        memory_path.unlink()
