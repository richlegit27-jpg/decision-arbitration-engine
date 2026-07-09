from __future__ import annotations


class RuntimeCompressionService:
    def __init__(self, max_history=5, max_steps=8, max_engines=12):
        self.max_history = max_history
        self.max_steps = max_steps
        self.max_engines = max_engines

    def compress(self, runtime_state):
        if not isinstance(runtime_state, dict):
            return {}

        return {
            "ok": runtime_state.get("ok", True),
            "status": runtime_state.get("status"),
            "runtime_route": runtime_state.get("runtime_route"),
            "runtime_signal": runtime_state.get("runtime_signal"),
            "final_action": runtime_state.get("final_action"),
            "reflection": self._compress_reflection(
                runtime_state.get("reflection")
            ),
            "governor": self._compress_governor(
                runtime_state.get("runtime_governor")
            ),
            "policy": self._compress_policy(
                runtime_state.get("runtime_adaptive_policy")
            ),
            "prediction": self._compress_prediction(
                runtime_state.get("runtime_prediction")
            ),
            "graph": self._compress_graph(
                runtime_state
            ),
            "orchestration": self._compress_orchestration(
                runtime_state.get("orchestration_report")
            ),
        }

    def _compress_reflection(self, reflection):
        if not isinstance(reflection, dict):
            return {}

        return {
            "signal": reflection.get("signal"),
            "next_action": reflection.get("next_action"),
            "reason": reflection.get("reason"),
        }

    def _compress_governor(self, governor):
        if not isinstance(governor, dict):
            return {}

        return {
            "selected_action": governor.get("selected_action"),
            "selected_engine": governor.get("selected_engine"),
            "reason": governor.get("reason"),
        }

    def _compress_policy(self, policy):
        if not isinstance(policy, dict):
            return {}

        adaptive = policy.get("adaptive_policy")
        trend = policy.get("trend")

        if not isinstance(adaptive, dict):
            adaptive = {}

        if not isinstance(trend, dict):
            trend = {}

        return {
            "runtime_health": adaptive.get("runtime_health"),
            "allow_retry": adaptive.get("allow_retry"),
            "allow_mutation": adaptive.get("allow_mutation"),
            "allow_evolution": adaptive.get("allow_evolution"),
            "instability_ratio": trend.get("instability_ratio"),
            "stability_ratio": trend.get("stability_ratio"),
            "total_cycles": trend.get("total_cycles"),
        }

    def _compress_prediction(self, prediction):
        if not isinstance(prediction, dict):
            return {}

        return {
            "predicted_state": prediction.get("predicted_state"),
            "risk_forecast": prediction.get("risk_forecast"),
            "prediction_reason": prediction.get("prediction_reason"),
            "success_rate": prediction.get("success_rate"),
        }

    def _compress_graph(self, runtime_state):
        graph_summary = runtime_state.get("runtime_graph_summary")
        graph_memory = runtime_state.get("runtime_graph_memory")
        graph_patterns = runtime_state.get("runtime_graph_patterns")

        if not isinstance(graph_summary, dict):
            graph_summary = {}

        if not isinstance(graph_memory, dict):
            graph_memory = {}

        if not isinstance(graph_patterns, dict):
            graph_patterns = {}

        return {
            "summary": graph_summary.get("summary"),
            "event_count": graph_memory.get("event_count"),
            "hot_paths": graph_patterns.get("hot_paths", [])[:3],
        }

    def _compress_orchestration(self, orchestration):
        if not isinstance(orchestration, dict):
            return {}

        fusion = orchestration.get("fusion")
        plan = orchestration.get("plan")
        report = orchestration.get("report")

        if not isinstance(fusion, dict):
            fusion = {}

        if not isinstance(plan, dict):
            plan = {}

        if not isinstance(report, dict):
            report = {}

        steps = plan.get("steps")
        results = report.get("results")

        if not isinstance(steps, list):
            steps = []

        if not isinstance(results, list):
            results = []

        return {
            "recommended_action": fusion.get("recommended_action"),
            "confidence": fusion.get("confidence"),
            "signals": fusion.get("signals", [])[:12],
            "plan_id": plan.get("plan_id"),
            "step_count": len(steps),
            "top_steps": self._compress_steps(
                steps[: self.max_steps]
            ),
            "result_count": len(results),
        }

    def _compress_steps(self, steps):
        compressed = []

        for step in steps:
            if not isinstance(step, dict):
                continue

            result = step.get("result")

            if not isinstance(result, dict):
                result = {}

            compressed.append(
                {
                    "engine": step.get("engine"),
                    "action": result.get("action") or step.get("action"),
                    "status": step.get("status"),
                    "score": step.get("score"),
                    "ok": result.get("ok"),
                    "message": result.get("message"),
                }
            )

        return compressed

