from __future__ import annotations

import json
from pathlib import Path


class RuntimePersistenceService:
    def __init__(
        self,
        save_file="data/runtime_persistent_state.json",
    ):
        self.save_path = Path(save_file)

    def _safe_dict(
        self,
        value,
    ):
        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def save(
        self,
        runtime_result=None,
    ):
        runtime_result = self._safe_dict(
            runtime_result
        )

        compressed_runtime = self._safe_dict(
            runtime_result.get(
                "compressed_runtime"
            )
        )

        execution_state = self._safe_dict(
            runtime_result.get(
                "execution_state"
            )
        )

        if not execution_state:
            execution_state = self._safe_dict(
                compressed_runtime.get(
                    "execution_state"
                )
            )

        payload = {
            "compressed_runtime": compressed_runtime,
            "execution_state": execution_state,
            "runtime_summary_memory": (
                execution_state.get(
                    "runtime_summary_memory",
                    []
                )
            ),
            "risk_memory_state": (
                execution_state.get(
                    "risk_memory_state",
                    {}
                )
            ),
            "persistent_risk_score": (
                execution_state.get(
                    "persistent_risk_score",
                    0
                )
            ),
            "persistent_recovery_pressure": (
                execution_state.get(
                    "persistent_recovery_pressure",
                    0
                )
            ),
            "runtime_identity": (
                execution_state.get(
                    "runtime_identity",
                    {}
                )
            ),
            "runtime_goal": (
                execution_state.get(
                    "runtime_goal",
                    {}
                )
            ),
            "runtime_world_model": (
                execution_state.get(
                    "runtime_world_model",
                    {}
                )
            ),
            "runtime_policy_enforcement": (
                execution_state.get(
                    "runtime_policy_enforcement",
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
                compressed_runtime.get(
                    "runtime_health"
                )
                or execution_state.get(
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
            "persisted_keys": list(
                payload.keys()
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
                payload = json.load(f)

            return (
                payload
                if isinstance(payload, dict)
                else {}
            )

        except Exception:
            return {}

    def hydrate_execution_state(
        self,
        execution_state=None,
    ):
        execution_state = self._safe_dict(
            execution_state
        )

        persisted = self.load()

        if not isinstance(
            persisted,
            dict,
        ):
            return execution_state

        persisted_execution_state = self._safe_dict(
            persisted.get(
                "execution_state"
            )
        )

        execution_state.update(
            persisted_execution_state
        )

        for key in [
            "runtime_summary_memory",
            "risk_memory_state",
            "persistent_risk_score",
            "persistent_recovery_pressure",
            "runtime_identity",
            "runtime_goal",
            "runtime_world_model",
            "runtime_policy_enforcement",
            "runtime_health",
        ]:
            if key in persisted:
                execution_state[key] = persisted.get(
                    key
                )

        execution_state[
            "runtime_persistence_hydrated"
        ] = True

        return execution_state