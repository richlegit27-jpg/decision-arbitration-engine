from nova_backend.services.nova_behavior_signal_builder import (
    NovaBehaviorSignalBuilder,
)


print("NOVA BEHAVIOR SIGNAL BUILDER SMOKE")
print("=" * 45)


builder = NovaBehaviorSignalBuilder()


result = builder.build(
    user_text="remember our project",
    assistant_text="I can help continue the project plan",
    context=""
)


assert "continuity" in result
assert "helpfulness" in result
assert "issues" in result


print("PASS builds behavior signals")


failed = builder.build(
    None,
    None,
    None,
)


assert "issues" in failed

print("PASS handles empty input")


print()
print(
    "NOVA BEHAVIOR SIGNAL BUILDER SMOKE PASSED"
)