from nova_backend.services.model_gateway_service import (
    resolve_nova_task_model,
)


def assert_equal(name, actual, expected):
    if actual != expected:
        raise AssertionError(
            f"{name} FAILED: {actual} != {expected}"
        )

    print(f"PASS {name}")


def main():
    coding = resolve_nova_task_model(
        text="Fix this Python API bug"
    )

    assert_equal(
        "coding_route",
        coding,
        "gpt-5.4",
    )

    vision = resolve_nova_task_model(
        text="Analyze this image"
    )

    assert_equal(
        "vision_route",
        vision,
        "gpt-4o-mini",
    )

    fast = resolve_nova_task_model(
        text="Tell me a joke"
    )

    assert_equal(
        "default_fast_route",
        fast,
        "gpt-4.1-mini",
    )

    manual = resolve_nova_task_model(
        model="nova-smart",
        text="simple question",
    )

    assert_equal(
        "manual_override",
        manual,
        "gpt-5.4",
    )

    print()
    print("NOVA MODEL ROUTING SMOKE PASSED")


if __name__ == "__main__":
    main()