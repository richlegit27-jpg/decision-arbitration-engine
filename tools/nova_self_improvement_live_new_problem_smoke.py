"""
NOVA SELF IMPROVEMENT LIVE NEW PROBLEM SMOKE

Tests:
new behavior problem
        |
        v
self improvement coordinator
        |
        v
mission creation
"""

from nova_backend.services.nova_self_improvement_coordinator import (
    evaluate_self_improvement,
)


print(
    "NOVA SELF IMPROVEMENT LIVE NEW PROBLEM SMOKE"
)

print(
    "============================================"
)


signal = {

    "recommended_focus": {

        "focus":
            "weak_memory_consolidation",

        "priority":
            "critical",

        "reason":
            "memory consolidation needs improvement",

    }

}


print(
    "\nNEW SIGNAL:"
)

print(
    signal
)


result = (
    evaluate_self_improvement(
        signal
    )
)


print(
    "\nRESULT:"
)

print(
    result
)


if not result.get(
    "improved"
):

    raise Exception(
        "FAIL new improvement was not accepted"
    )


if not result.get(
    "mission"
):

    raise Exception(
        "FAIL mission was not created"
    )


print(
    "\nPASS new improvement mission created"
)