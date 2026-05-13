from __future__ import annotations

import json
from pathlib import Path


class RuntimePersistenceService:
    def __init__(
        self,
        save_file="data/runtime_persistent_state.json",
    ):
        self.save_path = Path(save_file)

    def save(
        self,
        runtime_result=None,
    ):
        runtime_result = runtime_result or {}

        payload = {
            "compressed_runtime": (
                runtime_result.get(
                    "compressed_runtime",
                    {}
                )
            ),
            "runtime_drift_memory": (
                runtime_result.get(
                    "runtime_drift_memory",
                    {}
                )
            ),
            "runtime_graph_patterns": (
                runtime_result.get(
                    "runtime_graph_patterns",
                    {}
                )
            ),
            "runtime_health": (
                runtime_result.get(
                    "compressed_runtime",
                    {}
                ).get(
                    "runtime_health"
                )
            ),
        }

        self.save_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with open(
            self.save_path,
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                payload,
                f,
                indent=2,
            )

        return {
            "ok": True,
            "save_file": str(
                self.save_path
            ),
        }

    def load(
        self,
    ):
        if not self.save_path.exists():
            return {}

        try:
            with open(
                self.save_path,
                "r",
                encoding="utf-8",
            ) as f:
                return json.load(f)

        except Exception:
            return {}