from __future__ import annotations

import json
from pathlib import Path


class RuntimeDriftMemoryService:
    def __init__(
        self,
        memory_file="data/runtime_drift_memory.json",
    ):
        self.memory_path = Path(memory_file)

    def record(
        self,
        runtime_prediction=None,
        runtime_policy=None,
        runtime_signal=None,
    ):
        memory = self.load_memory()

        history = memory.get(
            "history",
            [],
        )

        history.append(
            {
                "predicted_state": (
                    runtime_prediction or {}
                ).get(
                    "predicted_state"
                ),
                "risk_forecast": (
                    runtime_prediction or {}
                ).get(
                    "risk_forecast"
                ),
                "runtime_health": (
                    runtime_policy or {}
                ).get(
                    "runtime_health"
                ),
                "runtime_signal": runtime_signal,
            }
        )

        history = history[-100:]

        unstable = [
            x for x in history
            if x.get("predicted_state")
            == "unstable"
        ]

        stable = [
            x for x in history
            if x.get("predicted_state")
            == "stable"
        ]

        drift_state = "stable"

        if len(unstable) > len(stable):
            drift_state = "destabilizing"

        payload = {
            "history": history,
            "history_count": len(history),
            "unstable_count": len(unstable),
            "stable_count": len(stable),
            "drift_state": drift_state,
        }

        self.memory_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with open(
            self.memory_path,
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                payload,
                f,
                indent=2,
            )

        return payload

    def load_memory(
        self,
    ):
        if not self.memory_path.exists():
            return {}

        try:
            with open(
                self.memory_path,
                "r",
                encoding="utf-8",
            ) as f:
                return json.load(f)

        except Exception:
            return {}