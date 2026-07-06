import os
import json


class FileService:
    """
    Unified safe file system layer for Nova
    """

    # =========================================================
    # ENSURE DIRECTORY EXISTS
    # =========================================================
    def ensure_dir(self, file_path: str):
        directory = os.path.dirname(file_path)

        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    # =========================================================
    # WRITE TEXT FILE
    # =========================================================
    def write_text(self, file_path: str, content: str):
        self.ensure_dir(file_path)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {"ok": True, "path": file_path}

    # =========================================================
    # READ TEXT FILE
    # =========================================================
    def read_text(self, file_path: str):
        if not os.path.exists(file_path):
            return {"ok": False, "error": "File not found"}

        with open(file_path, "r", encoding="utf-8") as f:
            return {"ok": True, "content": f.read()}

    # =========================================================
    # WRITE JSON
    # =========================================================
    def write_json(self, file_path: str, data: dict):
        self.ensure_dir(file_path)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return {"ok": True, "path": file_path}

    # =========================================================
    # READ JSON
    # =========================================================
    def read_json(self, file_path: str):
        if not os.path.exists(file_path):
            return {"ok": False, "error": "File not found"}

        with open(file_path, "r", encoding="utf-8") as f:
            return {"ok": True, "data": json.load(f)}