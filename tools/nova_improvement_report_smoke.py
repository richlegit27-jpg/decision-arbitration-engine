from nova_backend.services.nova_improvement_report_service import (
    create_improvement_report,
)


print(
    "NOVA IMPROVEMENT REPORT SMOKE"
)

print(
    "============================="
)


report = create_improvement_report(
    recommendation={
        "problem": "continuity",
        "reason": "continuity detected repeatedly",
        "recommended_upgrade":
            "Improve conversation recall",
        "target_system":
            "conversation memory system",
    },

    decision={
        "decision":
            "consider_upgrade",
    },

    proposal={
        "risk":
            "low",
    },

    mission_proposal={
        "status":
            "proposal",

        "approval_required":
            True,
    },
)


assert (
    report["type"]
    ==
    "improvement_report"
)

print(
    "PASS creates report"
)


assert (
    report["detected_problem"]
    ==
    "continuity"
)

print(
    "PASS preserves detected problem"
)


assert (
    report["approval_required"]
    is True
)

print(
    "PASS preserves approval boundary"
)


assert (
    report["mission_status"]
    ==
    "proposal"
)

print(
    "PASS preserves mission state"
)


print(
    "NOVA IMPROVEMENT REPORT SMOKE PASSED"
)