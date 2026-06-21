from nova_backend.services.interpretation_service import interpret_user_text

CASES = [
    ("tucker carlson news", "web"),
    ("news", "web"),
    ("latest news", "web"),
    ("what's going on with fifa", "web"),
    ("anything new with trump", "web"),
    ("what were we talking about", "memory"),
    ("remember what i said about login", "memory"),
    ("attachment is broken", "attachments"),
    ("what is in this file", "attachments"),
    ("k", "chat"),
    ("k", "execution"),
    ("fix login shit", "planner"),
    ("memory is stuck loading", "memory"),
    ("source cards are showing 3 rows", "project_debug"),
]

for text, expected_route in CASES:
    kwargs = {}
    if text == "k" and expected_route == "execution":
        kwargs["has_active_execution"] = True

    result = interpret_user_text(text, **kwargs)
    route = result["route_hint"]

    print(f"{text!r}")
    print("  intent:", result["intent"])
    print("  route :", route)
    print("  rewrite:", result["rewritten_text"])
    print("  reason:", result["reason"])

    assert route == expected_route, f"{text!r}: expected {expected_route}, got {route}"

print("INTERPRETATION_LAYER_SMOKE_PASS")


