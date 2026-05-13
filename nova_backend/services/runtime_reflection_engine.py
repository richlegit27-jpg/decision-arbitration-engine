from nova_backend.services.runtime_engine_base import RuntimeEngineBase


class RuntimeReflectionEngine(RuntimeEngineBase):
    def __init__(self):
        super().__init__(
            name="runtime_reflection_engine",
            tags=[
                "reflection",
                "learning",
                "runtime",
            ],
        )

    def execute(
        self,
        context=None,
    ):
        context = self._safe_dict(context)

        runtime_status = context.get("runtime_status")
        execution_status = self._safe_str(
            context.get("execution_status")
        ).lower()

        debug_issues = self._safe_list(
            context.get("debug_issues")
        )

        healing_applied = self._safe_list(
            context.get("healing_applied")
        )

        lessons = []

        if runtime_status is False:
            lessons.append(
                {
                    "type": "runtime_failure",
                    "lesson": "Runtime cycle failed and should be inspected before continuing autonomy.",
                }
            )

        if execution_status in {
            "failed",
            "error",
        }:
            lessons.append(
                {
                    "type": "execution_failure",
                    "lesson": "Execution failure should trigger repair before new planning.",
                }
            )

        if debug_issues:
            lessons.append(
                {
                    "type": "debug_signal",
                    "lesson": "Debug issues should increase priority for debug and repair engines.",
                    "issues": debug_issues,
                }
            )

        if healing_applied:
            lessons.append(
                {
                    "type": "healing_signal",
                    "lesson": "Healing actions were applied and should be verified.",
                    "healing_applied": healing_applied,
                }
            )

        if not lessons:
            lessons.append(
                {
                    "type": "stable_cycle",
                    "lesson": "Runtime cycle appears stable.",
                }
            )

        return {
            "ok": True,
            "action": "runtime_reflection_completed",
            "message": "Runtime reflection completed.",
            "lessons": lessons,
            "lesson_count": len(lessons),
        }