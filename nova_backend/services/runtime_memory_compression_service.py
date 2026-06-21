class RuntimeMemoryCompressionService:
    def __init__(
        self,
        history_limit=25,
        summary_limit=10,
        max_raw_events=None,
        *args,
        **kwargs,
    ):
        self.history_limit = (
            max_raw_events
            if isinstance(max_raw_events, int)
            else history_limit
        )

        self.summary_limit = summary_limit

    def _safe_list(
        self,
        value,
    ):
        return value if isinstance(value, list) else []

    def _safe_dict(
        self,
        value,
    ):
        return value if isinstance(value, dict) else {}

    def _score_item(
        self,
        item,
    ):
        if not isinstance(item, dict):
            return 0

        score = 1

        signal = str(
            item.get("runtime_signal")
            or item.get("signal")
            or ""
        ).lower()

        action = str(
            item.get("final_action")
            or item.get("action")
            or ""
        ).lower()

        if "fail" in signal or "error" in signal:
            score += 5

        if "anomaly" in signal:
            score += 4

        if "recovery" in signal:
            score += 4

        if "rollback" in signal:
            score += 5

        if "repair" in action:
            score += 4

        if "recover" in action:
            score += 4

        if item.get("anomaly_detected"):
            score += 4

        if item.get("recovery_mode"):
            score += 3

        if item.get("runtime_policy_shift"):
            score += 3

        return score

    def _build_pressure_summary(
        self,
        execution_state,
    ):
        execution_state = self._safe_dict(
            execution_state
        )

        runtime_signal = str(
            execution_state.get(
                "runtime_signal",
                ""
            )
            or ""
        ).lower()

        runtime_health = str(
            execution_state.get(
                "runtime_health",
                ""
            )
            or ""
        ).lower()

        runtime_identity_state = self._safe_dict(
            self._safe_dict(
                execution_state.get(
                    "runtime_identity"
                )
            ).get(
                "identity_state"
            )
        )

        runtime_identity = str(
            runtime_identity_state.get(
                "runtime_identity",
                ""
            )
            or ""
        ).lower()

        pressure_summary = {
            "label": "runtime_pressure",
            "importance_score": 0,
            "top_events": [],
        }

        if "failure" in runtime_signal:
            pressure_summary["importance_score"] += 15
            pressure_summary["top_events"].append(
                {
                    "runtime_signal": runtime_signal,
                    "event_type": "failure_signal",
                }
            )

        if runtime_health == "unstable":
            pressure_summary["importance_score"] += 20
            pressure_summary["top_events"].append(
                {
                    "runtime_signal": "unstable_runtime",
                    "event_type": "runtime_health",
                }
            )

        if runtime_identity == "cooldown_runtime":
            pressure_summary["importance_score"] += 10
            pressure_summary["top_events"].append(
                {
                    "runtime_signal": "cooldown_runtime",
                    "event_type": "stabilization_mode",
                }
            )

        return pressure_summary

    def _build_risk_memory_state(
        self,
        summary_memory,
    ):
        summary_memory = self._safe_list(
            summary_memory
        )

        persistent_risk_score = 0
        persistent_recovery_pressure = 0

        for summary in summary_memory:

            if not isinstance(summary, dict):
                continue

            importance_score = int(
                summary.get("importance_score", 0)
                or 0
            )

            persistent_risk_score += importance_score

            for event in self._safe_list(
                summary.get("top_events")
            ):
                if not isinstance(event, dict):
                    continue

                signal = str(
                    event.get("runtime_signal")
                    or ""
                ).lower()

                action = str(
                    event.get("final_action")
                    or ""
                ).lower()

                if (
                    "recovery" in signal
                    or "repair" in action
                    or "rollback" in signal
                    or "anomaly" in signal
                    or "failure" in signal
                    or "unstable" in signal
                    or "cooldown" in signal
                ):
                    persistent_recovery_pressure += 1

        risk_level = "low"

        if persistent_risk_score >= 80:
            risk_level = "high"

        elif persistent_risk_score >= 40:
            risk_level = "medium"

        return {
            "persistent_risk_score": persistent_risk_score,
            "persistent_recovery_pressure": persistent_recovery_pressure,
            "risk_level": risk_level,
            "summary_count": len(summary_memory),
        }

    def _summarize_items(
        self,
        label,
        items,
    ):
        items = self._safe_list(items)

        if not items:
            return None

        signals = []
        actions = []
        scored_items = []

        for item in items:
            if not isinstance(item, dict):
                continue

            signal = item.get("runtime_signal")
            action = item.get("final_action")

            if signal:
                signals.append(str(signal))

            if action:
                actions.append(str(action))

            scored_items.append(
                {
                    "score": self._score_item(item),
                    "runtime_signal": signal,
                    "final_action": action,
                    "cycle": item.get("cycle"),
                }
            )

        scored_items = sorted(
            scored_items,
            key=lambda entry: entry.get("score", 0),
            reverse=True,
        )

        return {
            "label": label,
            "compressed_count": len(items),
            "importance_score": sum(
                item.get("score", 0)
                for item in scored_items
            ),
            "top_events": scored_items[:5],
            "recent_signals": signals[-5:],
            "recent_actions": actions[-5:],
        }

    def _compress_history(
        self,
        execution_state,
        key,
    ):
        history = self._safe_list(
            execution_state.get(key)
        )

        if len(history) <= self.history_limit:
            return execution_state

        older_items = history[:-self.history_limit]
        kept_items = history[-self.history_limit:]

        summary = self._summarize_items(
            label=key,
            items=older_items,
        )

        summary_memory = self._safe_list(
            execution_state.get("runtime_summary_memory")
        )

        if summary:
            summary_memory.append(summary)

            summary_memory = sorted(
                summary_memory,
                key=lambda item: item.get(
                    "importance_score",
                    0,
                ),
                reverse=True,
            )

            summary_memory = summary_memory[:self.summary_limit]

        risk_memory_state = self._build_risk_memory_state(
            summary_memory
        )

        execution_state[key] = kept_items
        execution_state["runtime_summary_memory"] = summary_memory
        execution_state["risk_memory_state"] = risk_memory_state
        execution_state["persistent_risk_score"] = (
            risk_memory_state.get("persistent_risk_score", 0)
        )
        execution_state["persistent_recovery_pressure"] = (
            risk_memory_state.get(
                "persistent_recovery_pressure",
                0,
            )
        )

        return execution_state

    def compress(
        self,
        execution_state=None,
    ):
        execution_state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        keys = [
            "runtime_history",
            "prediction_history",
            "goal_history",
            "identity_history",
            "plan_history",
            "runtime_autonomous_memory",
        ]

        compressed_keys = []

        for key in keys:
            before_count = len(
                self._safe_list(
                    execution_state.get(key)
                )
            )

            execution_state = self._compress_history(
                execution_state=execution_state,
                key=key,
            )

            after_count = len(
                self._safe_list(
                    execution_state.get(key)
                )
            )

            if after_count < before_count:
                compressed_keys.append(key)

        summary_memory = self._safe_list(
            execution_state.get("runtime_summary_memory")
        )

        pressure_summary = self._build_pressure_summary(
            execution_state
        )

        if pressure_summary.get(
            "importance_score",
            0,
        ) > 0:
            summary_memory.append(
                pressure_summary
            )

        summary_memory = sorted(
            summary_memory,
            key=lambda item: item.get(
                "importance_score",
                0,
            ),
            reverse=True,
        )

        summary_memory = summary_memory[:self.summary_limit]

        risk_memory_state = self._build_risk_memory_state(
            summary_memory
        )

        execution_state["runtime_summary_memory"] = summary_memory
        execution_state["risk_memory_state"] = risk_memory_state
        execution_state["persistent_risk_score"] = (
            risk_memory_state.get("persistent_risk_score", 0)
        )
        execution_state["persistent_recovery_pressure"] = (
            risk_memory_state.get(
                "persistent_recovery_pressure",
                0,
            )
        )
        execution_state["runtime_memory_compression_active"] = True

        return {
            "ok": True,
            "compressed_keys": compressed_keys,
            "execution_state": execution_state,
            "summary_count": len(summary_memory),
            "risk_memory_state": risk_memory_state,
        }

