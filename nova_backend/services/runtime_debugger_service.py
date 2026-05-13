class RuntimeDebuggerService:
    def __init__(self):
        self.last_report = {}

    def _safe_dict(self, value):
        return value if isinstance(value, dict) else {}

    def _safe_list(self, value):
        return value if isinstance(value, list) else []

    def inspect_runtime_result(self, runtime_result):
        runtime_result = self._safe_dict(runtime_result)

        execution = self._safe_dict(
            runtime_result.get("execution")
        )

        reflection = self._safe_dict(
            runtime_result.get("reflection")
        )

        decision = self._safe_dict(
            runtime_result.get("decision")
        )

        issues = []

        if not runtime_result.get("ok"):
            issues.append("runtime_result_not_ok")

        if execution.get("failed_count", 0) > 0:
            issues.append("execution_has_failed_steps")

        if not runtime_result.get("trace_id"):
            issues.append("missing_trace_id")

        if not runtime_result.get("replay_id"):
            issues.append("missing_replay_id")

        if not decision.get("action"):
            issues.append("missing_decision_action")

        if not reflection.get("signal"):
            issues.append("missing_reflection_signal")

        report = {
            "ok": len(issues) == 0,
            "issues": issues,
            "execution_status": execution.get("status"),
            "failed_count": execution.get("failed_count", 0),
            "reflection_signal": reflection.get("signal"),
            "decision_action": decision.get("action"),
            "final_action": runtime_result.get("final_action"),
            "trace_id": runtime_result.get("trace_id"),
            "replay_id": runtime_result.get("replay_id"),
        }

        self.last_report = report

        return report

    def inspect_replay_explanation(self, replay_explanation):
        replay_explanation = self._safe_dict(replay_explanation)

        summary = self._safe_dict(
            replay_explanation.get("summary")
        )

        decision_report = self._safe_dict(
            replay_explanation.get("decision_report")
        )

        graph_report = self._safe_dict(
            replay_explanation.get("graph_report")
        )

        execution_report = self._safe_dict(
            replay_explanation.get("execution_report")
        )

        issues = []

        if not replay_explanation.get("ok"):
            issues.append("replay_explanation_not_ok")

        if not summary.get("trace_id"):
            issues.append("missing_replay_trace_id")

        if decision_report.get("decision_count", 0) <= 0:
            issues.append("missing_decision_trace")

        if graph_report.get("graph_change_count", 0) <= 0:
            issues.append("missing_graph_trace")

        if execution_report.get("execution_change_count", 0) <= 0:
            issues.append("missing_execution_trace")

        report = {
            "ok": len(issues) == 0,
            "issues": issues,
            "trace_id": summary.get("trace_id"),
            "event_count": summary.get("event_count", 0),
            "event_types": summary.get("event_types", []),
            "decision_count": decision_report.get("decision_count", 0),
            "graph_change_count": graph_report.get(
                "graph_change_count",
                0,
            ),
            "execution_change_count": execution_report.get(
                "execution_change_count",
                0,
            ),
        }

        self.last_report = report

        return report

    def detect_instability_patterns(self, runtime_history):
        runtime_history = self._safe_list(runtime_history)

        issues = []

        failed_cycles = [
            item
            for item in runtime_history
            if isinstance(item, dict)
            and item.get("failure_type")
        ]

        repeated_actions = {}

        for item in runtime_history:
            if not isinstance(item, dict):
                continue

            action = item.get("final_action")

            if not action:
                continue

            repeated_actions[action] = (
                repeated_actions.get(action, 0) + 1
            )

        repeated_hot_actions = [
            action
            for action, count in repeated_actions.items()
            if count >= 5
        ]

        if len(failed_cycles) >= 3:
            issues.append("repeated_failure_cycles")

        if repeated_hot_actions:
            issues.append("repeated_runtime_actions")

        return {
            "ok": len(issues) == 0,
            "issues": issues,
            "history_count": len(runtime_history),
            "failed_cycle_count": len(failed_cycles),
            "repeated_actions": repeated_actions,
            "repeated_hot_actions": repeated_hot_actions,
        }

    def suggest_repairs(
        self,
        runtime_result=None,
        replay_explanation=None,
        runtime_history=None,
    ):
        runtime_report = self.inspect_runtime_result(
            runtime_result or {}
        )

        replay_report = self.inspect_replay_explanation(
            replay_explanation or {}
        )

        instability_report = self.detect_instability_patterns(
            runtime_history or []
        )

        suggestions = []

        issues = (
            runtime_report.get("issues", [])
            + replay_report.get("issues", [])
            + instability_report.get("issues", [])
        )

        if "missing_trace_id" in issues:
            suggestions.append(
                "Ensure observability.start_trace returns a trace_id."
            )

        if "missing_replay_id" in issues:
            suggestions.append(
                "Ensure replay.build_replay runs before returning runtime result."
            )

        if "missing_decision_trace" in issues:
            suggestions.append(
                "Ensure observability.record_decision is called every runtime cycle."
            )

        if "missing_graph_trace" in issues:
            suggestions.append(
                "Ensure observability.record_graph_change is called after graph pipeline."
            )

        if "missing_execution_trace" in issues:
            suggestions.append(
                "Ensure observability.record_execution is called before ending trace."
            )

        if "execution_has_failed_steps" in issues:
            suggestions.append(
                "Inspect failed execution step and route through repair_only mode."
            )

        if "repeated_failure_cycles" in issues:
            suggestions.append(
                "Throttle mutation/evolution and force graph repair mode."
            )

        if "repeated_runtime_actions" in issues:
            suggestions.append(
                "Check governor policy; repeated action loop may need cooldown."
            )

        if not suggestions:
            suggestions.append(
                "No repair required. Runtime trace appears healthy."
            )

        return {
            "ok": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions,
            "runtime_report": runtime_report,
            "replay_report": replay_report,
            "instability_report": instability_report,
        }

    def get_last_report(self):
        return self.last_report