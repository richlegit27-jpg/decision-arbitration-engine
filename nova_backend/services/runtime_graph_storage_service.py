import json
import os


class RuntimeGraphStorageService:

    def __init__(
        self,
        storage_path=None,
    ):

        self.storage_path = (
            storage_path
            or "data/runtime_graph_memory.json"
        )

        self._ensure_parent_dir()

    def _ensure_parent_dir(self):

        parent = os.path.dirname(
            self.storage_path
        )

        if parent:

            os.makedirs(
                parent,
                exist_ok=True,
            )

    def _safe_dict(self, value):

        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def save_snapshot(
        self,
        snapshot,
    ):

        snapshot = self._safe_dict(
            snapshot
        )

        with open(
            self.storage_path,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                snapshot,
                f,
                indent=2,
            )

        return {
            "ok": True,
            "storage_path": self.storage_path,
        }

    def load_snapshot(self):

        if not os.path.exists(
            self.storage_path
        ):

            return {
                "nodes": {},
                "edges": [],
            }

        try:

            with open(
                self.storage_path,
                "r",
                encoding="utf-8",
            ) as f:

                data = json.load(f)

            return (
                data
                if isinstance(data, dict)
                else {
                    "nodes": {},
                    "edges": [],
                }
            )

        except Exception:

            return {
                "nodes": {},
                "edges": [],
            }