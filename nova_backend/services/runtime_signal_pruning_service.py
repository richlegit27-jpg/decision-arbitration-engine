from __future__ import annotations


class RuntimeSignalPruningService:
    def __init__(
        self,
        max_signals=8,
        max_hot_paths=3,
        max_engines=6,
    ):
        self.max_signals = max_signals
        self.max_hot_paths = max_hot_paths
        self.max_engines = max_engines

    def prune(
        self,
        runtime_result,
    ):
        if not isinstance(runtime_result, dict):
            return {}

        orchestration = runtime_result.get(
            "orchestration_report"
        ) or {}

        fusion = orchestration.get("fusion") or {}
        report = orchestration.get("report") or {}

        signals = fusion.get("signals") or []

        pruned_signals = self._dedupe(
            signals
        )[: self.max_signals]

        graph_patterns = runtime_result.get(
            "runtime_graph_patterns"
        ) or {}

        hot_paths = (
            graph_patterns.get("hot_paths")
            or []
        )[: self.max_hot_paths]

        engine_states = (
            report.get("engine_states")
            or {}
        )

        top_engines = self._top_engines(
            engine_states
        )

        return {
            "ok": True,
            "signals": pruned_signals,
            "hot_paths": hot_paths,
            "top_engines": top_engines,
            "signal_count": len(pruned_signals),
            "engine_count": len(top_engines),
        }

    def _dedupe(
        self,
        values,
    ):
        seen = set()
        result = []

        for value in values:
            if value in seen:
                continue

            seen.add(value)
            result.append(value)

        return result

    def _top_engines(
        self,
        engine_states,
    ):
        ranked = []

        for name, state in engine_states.items():

            if not isinstance(state, dict):
                continue

            ranked.append(
                {
                    "engine": name,
                    "status": state.get("status"),
                    "success_count": state.get(
                        "success_count",
                        0,
                    ),
                    "failure_count": state.get(
                        "failure_count",
                        0,
                    ),
                }
            )

        ranked.sort(
            key=lambda x: (
                x.get("success_count", 0)
                - x.get("failure_count", 0)
            ),
            reverse=True,
        )

        return ranked[: self.max_engines]

