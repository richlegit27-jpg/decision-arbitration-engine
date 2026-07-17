from __future__ import annotations

from typing import Dict, Any, List

from nova_backend.utils.file_utils import (
    load_json_file,
    save_json_file,
)


class UploadOwnershipService:

    def __init__(self, uploads_file="data/nova_upload_ownership.json"):
        self.uploads_file = uploads_file

        existing = load_json_file(
            self.uploads_file,
            {"uploads": []},
        )

        if not isinstance(existing, dict):
            save_json_file(
                self.uploads_file,
                {"uploads": []},
            )

    def _read_store(self) -> Dict[str, Any]:
        data = load_json_file(
            self.uploads_file,
            {"uploads": []},
        )

        if not isinstance(data, dict):
            return {"uploads": []}

        if not isinstance(data.get("uploads"), list):
            data["uploads"] = []

        return data

    def _write_store(self, data: Dict[str, Any]) -> None:
        save_json_file(
            self.uploads_file,
            data,
        )

    def register_upload(
        self,
        filename: str,
        owner_id: str,
    ) -> Dict[str, str]:

        data = self._read_store()

        record = {
            "filename": str(filename or "").strip(),
            "owner_id": str(owner_id or "").strip(),
        }

        data["uploads"].append(record)

        self._write_store(data)

        return record

    def belongs_to_user(
        self,
        filename: str,
        owner_id: str,
    ) -> bool:

        target = str(filename or "").strip()
        owner = str(owner_id or "").strip()

        for item in self._read_store().get("uploads", []):
            if (
                str(item.get("filename") or "").strip() == target
                and str(item.get("owner_id") or "").strip() == owner
            ):
                return True

        return False