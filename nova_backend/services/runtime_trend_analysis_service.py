class RuntimeTrendAnalysisService:
    def __init__(
        self,
        graph_memory=None,
    ):
        self.graph_memory = graph_memory

    def _safe_dict(
        self,
        value,
    ):
        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def _safe_list(
        self,
        value,
    ):
        return (
            value
            if isinstance(value, list)
            else []
        )

    def _memory(
        self,
    ):
        if not self.graph_memory:
            return {}

        if hasattr(
            self.graph_memory,
            "export_memory",
        ):
            return self.graph_memory.export_memory()

        return {
            "events": getattr(
                self.graph_memory,
                "events",
                [],
            )
        }

    def analyze(
        self,
    ):
        memory = self._safe_dict(
            self._memory()
        )

        events = self._safe_list(
            memory.get("events")
        )

        total_cycles = len(events)

        failure_cycles = 0
        success_cycles = 0

        retry_actions = 0
        stabilize_actions = 0

        throttled_cycles = 0

        graph_scores = []

        runtime_signals = {}

        for event in events:

            event = self._safe_dict(event)

            execution_summary = self._safe_dict(
                event.get("execution_summary")
            )

            execution_state = self._safe_dict(
                event.get("execution_state")
            )

            failed_count = int(
                execution_summary.get(
                    "failed_count",
                    0,
                )
                or 0
            )

            completed_count = int(
                execution_summary.get(
                    "completed_count",
                    0,
                )
                or 0
            )

            if failed_count:
                failure_cycles += 1

            if (
                completed_count
                and not failed_count
            ):
                success_cycles += 1

            governed_action = str(
                execution_state.get(
                    "governed_action"
                )
                or ""
            ).lower()

            if governed_action == "retry":
                retry_actions += 1

            if (
                governed_action
                == "preserve_success_state"
            ):
                stabilize_actions += 1

            healing_mode = str(
                execution_state.get(
                    "healing_mode"
                )
                or ""
            ).lower()

            if (
                healing_mode
                == "mutation_throttled"
            ):
                throttled_cycles += 1

            signal = str(
                execution_state.get(
                    "runtime_signal"
                )
                or "unknown"
            )

            runtime_signals[signal] = (
                runtime_signals.get(
                    signal,
                    0,
                )
                + 1
            )

            graph_memory = self._safe_dict(
                execution_state.get(
                    "graph_memory"
                )
            )

            graph_scores_map = self._safe_dict(
                graph_memory.get(
                    "graph_scores"
                )
            )

            for score in (
                graph_scores_map.values()
            ):

                try:
                    graph_scores.append(
                        float(score)
                    )
                except Exception:
                    pass

        average_graph_score = (
            sum(graph_scores)
            / len(graph_scores)
            if graph_scores
            else 0.0
        )

        stability_ratio = (
            success_cycles
            / total_cycles
            if total_cycles
            else 0.0
        )

        instability_ratio = (
            failure_cycles
            / total_cycles
            if total_cycles
            else 0.0
        )

        if instability_ratio >= 0.6:
            runtime_health = "unstable"

        elif stability_ratio >= 0.7:
            runtime_health = "stable"

        else:
            runtime_health = "recovering"

        recommendations = []

        if retry_actions >= 5:
            recommendations.append(
                "Reduce repetitive retry loops."
            )

        if throttled_cycles >= 3:
            recommendations.append(
                "Mutation throttling frequently activated."
            )

        if average_graph_score < 0.45:
            recommendations.append(
                "Graph confidence degraded."
            )

        if stabilize_actions >= 3:
            recommendations.append(
                "Runtime stabilization trend detected."
            )

        if not recommendations:
            recommendations.append(
                "Runtime trend appears healthy."
            )

        return {
            "ok": True,
            "total_cycles": total_cycles,
            "failure_cycles": failure_cycles,
            "success_cycles": success_cycles,
            "retry_actions": retry_actions,
            "stabilize_actions": stabilize_actions,
            "throttled_cycles": throttled_cycles,
            "average_graph_score": round(
                average_graph_score,
                6,
            ),
            "stability_ratio": round(
                stability_ratio,
                6,
            ),
            "instability_ratio": round(
                instability_ratio,
                6,
            ),
            "runtime_health": runtime_health,
            "runtime_signals": runtime_signals,
            "recommendations": recommendations,
        }

