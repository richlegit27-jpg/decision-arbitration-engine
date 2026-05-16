from __future__ import annotations

import json
import time
from pathlib import Path


class RuntimeSnapshotService:
    def __init__(
        self,
        snapshot_file="data/runtime_snapshot.json",
    ):
        self.snapshot_path = Path(snapshot_file)

    def save_snapshot(
        self,
        runtime_result,
    ):
        if not isinstance(runtime_result, dict):
            return {
                "ok": False,
                "reason": "invalid_runtime_result",
            }

        payload = {
            "saved_at": time.time(),
            "compressed_runtime": runtime_result.get(
                "compressed_runtime",
                {},
            ),
            "pruned_runtime_signals": runtime_result.get(
                "pruned_runtime_signals",
                {},
            ),
            "runtime_prediction": runtime_result.get(
                "runtime_prediction",
                {},
            ),
            "runtime_health": (
                runtime_result.get(
                    "runtime_adaptive_policy",
                    {},
                )
                .get(
                    "adaptive_policy",
                    {},
                )
                .get("runtime_health")
            ),
            "cycle_count": runtime_result.get(
                "cycle_count",
                0,
            ),
        }

        self.snapshot_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with open(
            self.snapshot_path,
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
            "snapshot_file": str(
                self.snapshot_path
            ),
        }

    def load_snapshot(
        self,
    ):
        if not self.snapshot_path.exists():
            return {}

        try:
            with open(
                self.snapshot_path,
                "r",
                encoding="utf-8",
            ) as f:
                return json.load(f)

        except Exception:
            return {}