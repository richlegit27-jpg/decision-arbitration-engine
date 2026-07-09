from __future__ import annotations

from typing import Any

from nova_backend.core.json_store import read_json, write_json
from nova_backend.core.text_utils import safe_list
from nova_backend.paths import ARTIFACTS_FILE


class ArtifactStore:
    def __init__(self, path=ARTIFACTS_FILE) -> None:
        self.path = path

    def load(self) -> list[dict[str, Any]]:
        data = read_json(self.path, [])
        return safe_list(data)

    def save(self, artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        clean = safe_list(artifacts)
        write_json(self.path, clean)
        return clean

    def all(self) -> list[dict[str, Any]]:
        return self.load()

