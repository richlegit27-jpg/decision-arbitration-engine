import time


class RuntimeSelfHealingService:
    def __init__(self):
        self.healing_history = []
        self.cooldowns = {}
        self.last_healing_report = {}

    def _safe_dict(self, value):
        return value if isinstance(value, dict) else {}

    def _safe_list(self, value):
        return value if isinstance(value, list) else []

    def _now(self):
        return time.time()

    def _cooldown_active(self, key, seconds=30):
        last_seen = self.cooldowns.get(key)

        if not last_seen:
            return False

        return (self._now() - last_seen) < seconds

    def _touch_cooldown(self, key):
        self.cooldowns[key] = self._now()

    def analyze_debug_report(self, debug_report):
        debug_report = self._safe_dict(debug_report)

        issues = self._safe_list(
            debug_report.get("issues")
        )

        suggestions = self._safe_list(
            debug_report.get("suggestions")
        )

        repair_actions = []

        if "execution_has_failed_steps" in issues:
            repair_actions.append(
                {
                    "action": "force_repair_mode",
                    "reason": "Execution has failed steps.",
                }
            )

        if "repeated_failure_cycles" in issues:
            repair_actions.append(
                {
                    "action": "throttle_mutation",
                    "reason": "Repeated runtime failures detected.",
                }
            )

        if "repeated_runtime_actions" in issues:
            repair_actions.append(
                {
                    "action": "apply_action_cooldown",
                    "reason": "Repeated runtime action loop detected.",
                }
            )

        if "missing_graph_trace" in issues:
            repair_actions.append(
                {
                    "action": "require_graph_trace",
                    "reason": "Graph trace missing from replay.",
                }
            )

        if "missing_execution_trace" in issues:
            repair_actions.append(
                {
                    "action": "require_execution_trace",
                    "reason": "Execution trace missing from replay.",
                }
            )

        if not repair_actions:
            repair_actions.append(
                {
                    "action": "no_repair_needed",
                    "reason": "Runtime appears healthy.",
                }
            )

        return {
            "ok": True,
            "issues": issues,
            "suggestions": suggestions,
            "repair_actions": repair_actions,
        }

    def build_healing_plan(
        self,
        debug_report=None,
        runtime_result=None,
        runtime_history=None,
    ):
        debug_report = self._safe_dict(debug_report)
        runtime_result = self._safe_dict(runtime_result)
        runtime_history = self._safe_list(runtime_history)

        analysis = self.analyze_debug_report(debug_report)

        repair_actions = self._safe_list(
            analysis.get("repair_actions")
        )

        final_action = runtime_result.get("final_action")

        plan_steps = []

        for repair in repair_actions:
            if not isinstance(repair, dict):
                continue

            action = repair.get("action")

            if action == "force_repair_mode":
                plan_steps.append(
                    {
                        "step": "set_runtime_mode",
                        "mode": "repair_only",
                        "reason": repair.get("reason"),
                    }
                )

            elif action == "throttle_mutation":
                plan_steps.append(
                    {
                        "step": "disable_mutation_temporarily",
                        "duration_seconds": 60,
                        "reason": repair.get("reason"),
                    }
                )

            elif action == "apply_action_cooldown":
                plan_steps.append(
                    {
                        "step": "cooldown_action",
                        "action": final_action,
                        "duration_seconds": 30,
                        "reason": repair.get("reason"),
                    }
                )

            elif action == "require_graph_trace":
                plan_steps.append(
                    {
                        "step": "enforce_graph_trace",
                        "reason": repair.get("reason"),
                    }
                )

            elif action == "require_execution_trace":
                plan_steps.append(
                    {
                        "step": "enforce_execution_trace",
                        "reason": repair.get("reason"),
                    }
                )

            elif action == "no_repair_needed":
                plan_steps.append(
                    {
                        "step": "observe_only",
                        "reason": repair.get("reason"),
                    }
                )

        plan = {
            "ok": True,
            "created_at": self._now(),
            "runtime_final_action": final_action,
            "history_count": len(runtime_history),
            "analysis": analysis,
            "steps": plan_steps,
        }

        self.last_healing_report = plan

        return plan

    def apply_healing_plan(
        self,
        execution_state=None,
        control=None,
        governor_policy=None,
        healing_plan=None,
    ):
        execution_state = self._safe_dict(execution_state)
        control = self._safe_dict(control)
        governor_policy = self._safe_dict(governor_policy)
        healing_plan = self._safe_dict(healing_plan)

        steps = self._safe_list(
            healing_plan.get("steps")
        )

        applied = []

        for step in steps:
            if not isinstance(step, dict):
                continue

            step_name = step.get("step")

            if step_name == "set_runtime_mode":
                control["mode"] = step.get(
                    "mode",
                    "repair_only",
                )

                allow = control.get("allow") or {}
                allow["mutation"] = False
                allow["compression"] = False
                allow["evolution"] = False
                allow["pruning"] = True
                control["allow"] = allow

                execution_state["healing_mode"] = (
                    "repair_only"
                )

                applied.append(step_name)

            elif step_name == "disable_mutation_temporarily":
                control["mutation_throttled"] = True

                allow = control.get("allow") or {}
                allow["mutation"] = False
                allow["evolution"] = False
                control["allow"] = allow

                self._touch_cooldown("mutation")

                execution_state["healing_mode"] = (
                    "mutation_throttled"
                )

                applied.append(step_name)

            elif step_name == "cooldown_action":
                action = step.get("action")

                if action:
                    self._touch_cooldown(
                        f"action:{action}"
                    )

                execution_state["healing_action_cooldown"] = (
                    action
                )

                applied.append(step_name)

            elif step_name == "enforce_graph_trace":
                execution_state["require_graph_trace"] = True
                applied.append(step_name)

            elif step_name == "enforce_execution_trace":
                execution_state["require_execution_trace"] = True
                applied.append(step_name)

            elif step_name == "observe_only":
                execution_state["healing_mode"] = (
                    "observe_only"
                )
                applied.append(step_name)

        report = {
            "ok": True,
            "applied": applied,
            "control": control,
            "governor_policy": governor_policy,
            "execution_state": execution_state,
        }

        self.healing_history.append(report)
        self.healing_history = self.healing_history[-100:]
        self.last_healing_report = report

        return report

    def should_block_action(self, action):
        if not action:
            return False

        return self._cooldown_active(
            f"action:{action}",
            seconds=30,
        )

    def should_throttle_mutation(self):
        return self._cooldown_active(
            "mutation",
            seconds=60,
        )

    def get_last_healing_report(self):
        return self.last_healing_report

    def get_healing_history(self, limit=25):
        return self.healing_history[-limit:]