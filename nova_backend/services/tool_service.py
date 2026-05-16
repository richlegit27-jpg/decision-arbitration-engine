import os
from typing import Dict, Any


class ToolService:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir or os.getcwd()

    # =========================
    # SAFE PATH
    # =========================
    def _safe_path(self, path: str) -> str:
        path = os.path.abspath(path)
        if not path.startswith(os.path.abspath(self.base_dir)):
            raise ValueError("Path outside allowed base directory")
        return path

    # =========================
    # READ FILE
    # =========================
    def read_file(self, path: str) -> Dict[str, Any]:
        try:
            safe = self._safe_path(path)
            with open(safe, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            return {
                "ok": True,
                "path": safe,
                "content": content[:20000],  # cap
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # =========================
    # WRITE FILE
    # =========================
    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        try:
            safe = self._safe_path(path)
            os.makedirs(os.path.dirname(safe), exist_ok=True)

            with open(safe, "w", encoding="utf-8") as f:
                f.write(content)

            return {"ok": True, "path": safe}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # =========================
    # APPEND FILE
    # =========================
    def append_file(self, path: str, content: str) -> Dict[str, Any]:
        try:
            safe = self._safe_path(path)
            with open(safe, "a", encoding="utf-8") as f:
                f.write(content)

            return {"ok": True, "path": safe}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # =========================
    # LIST FILES
    # =========================
    def list_dir(self, path: str) -> Dict[str, Any]:
        try:
            safe = self._safe_path(path)
            items = os.listdir(safe)
            return {"ok": True, "path": safe, "items": items[:200]}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # =========================
    # SEARCH TEXT
    # =========================
    def search_in_file(self, path: str, query: str) -> Dict[str, Any]:
        try:
            safe = self._safe_path(path)
            with open(safe, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            matches = []
            for i, line in enumerate(lines):
                if query.lower() in line.lower():
                    matches.append({"line": i + 1, "text": line.strip()})

            return {"ok": True, "matches": matches[:50]}
        except Exception as e:
            return {"ok": False, "error": str(e)}