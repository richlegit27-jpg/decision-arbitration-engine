"""
NOVA BEHAVIOR TO SELF IMPROVEMENT BRIDGE SMOKE
"""

from nova_backend.services.nova_behavior_memory import (
    behavior_memory,
)

from nova_backend.services.nova_self_improvement_coordinator import (
    evaluate_self_improvement,
)


print(
    "NOVA BEHAVIOR TO SELF IMPROVEMENT BRIDGE SMOKE"
)

print(
    "=============================================="
)


priority = (
    behavior_memory.create_improvement_priority()
)


print(
    "\nBEHAVIOR PRIORITY:"
)

print(
    priority
)


signal = {

    "recommended_focus":
        priority

}


print(
    "\nCOORDINATOR SIGNAL:"
)

print(
    signal
)


result = evaluate_self_improvement(
    signal
)


print(
    "\nRESULT:"
)

print(
    result
)


if not result:

    raise Exception(
        "FAIL no coordinator result"
    )


print(
    "\nPASS behavior bridge works"
)