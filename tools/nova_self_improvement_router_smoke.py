from nova_backend.services.nova_self_improvement_router import (
    build_self_improvement_signal
)


print(
    "NOVA SELF IMPROVEMENT ROUTER SMOKE"
)

print(
    "=================================="
)


report = {

    "recommended_focus":
    {

        "focus":
            "continuity",

        "priority":
            "medium",

        "reason":
            "continuity detected"
    }
}


signal = build_self_improvement_signal(
    report
)


assert (
    signal["analyze"]
    is True
)

print(
    "PASS detects improvement need"
)


assert (
    "continuity"
    in signal["reason"]
)

print(
    "PASS preserves reason"
)


print(
    "NOVA SELF IMPROVEMENT ROUTER SMOKE PASSED"
)