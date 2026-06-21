from nova_backend.services.runtime_engine_base import (
    RuntimeEngineBase,
)


class RuntimeSelfCheckEngine(
    RuntimeEngineBase
):
    def __init__(
        self,
    ):
        super().__init__(
            name="runtime_self_check_engine",
            tags=[
                "self_check",
                "verification",
                "stability",
                "runtime",
            ],
        )

    def execute(
        self,
        context=None,
    ):
        context = self._safe_dict(
            context
        )

        checks = []

        required_keys = [
            "runtime_status",
            "execution_status",
            "failed_count",
            "debug_issues",
            "trace_id",
            "replay_id",
        ]

        for key in required_keys:
            checks.append(
                {
                    "check": (
                        f"context_has_{key}"
                    ),
                    "ok": key in context,
                    "key": key,
                }
            )

        failed_checks = [
            check
            for check in checks
            if not check.get(
                "ok"
            )
        ]

        return {
            "ok": True,
            "action": (
                "runtime_self_check_completed"
            ),
            "checks": checks,
            "failed_checks": failed_checks,
            "failed_check_count": len(
                failed_checks
            ),
            "runtime_ready": not bool(
                failed_checks
            ),
        }

