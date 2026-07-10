from nova_backend.services.nova_project_brain_improvement_context import (
    build_project_brain_improvement_context
)


print(
    "NOVA PROJECT BRAIN IMPROVEMENT CONTEXT SMOKE"
)

print(
    "============================================"
)


context = (
    build_project_brain_improvement_context()
)


assert (
    "behavior_report"
    in context
)

print(
    "PASS includes behavior report"
)


assert (
    "self_improvement_signal"
    in context
)

print(
    "PASS includes improvement signal"
)


assert (
    "recommended_focus"
    in context
)

print(
    "PASS includes recommended focus"
)


print(
    "NOVA PROJECT BRAIN IMPROVEMENT CONTEXT SMOKE PASSED"
)