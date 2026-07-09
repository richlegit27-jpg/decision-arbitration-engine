from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def block_real_openai_clients(monkeypatch):
    """
    Test safety lock:
    pytest should never create a real OpenAI client.

    Individual tests should mock Nova service methods instead of hitting OpenAI.
    """

    try:
        import openai
    except Exception:
        yield
        return

    class BlockedOpenAIClient:
        def __init__(self, *args, **kwargs):
            raise AssertionError(
                "Blocked real OpenAI client during pytest. "
                "Mock chat_service.handle() or the specific service method instead."
            )

    monkeypatch.setattr(openai, "OpenAI", BlockedOpenAIClient, raising=False)
    monkeypatch.setattr(openai, "AsyncOpenAI", BlockedOpenAIClient, raising=False)

    yield


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


