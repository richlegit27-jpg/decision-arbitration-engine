from nova_backend.services.project_brain_decision_log_route_contract import (
    build_decision_log_api_payload,
    extract_user_text,
    is_decision_log_question,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    print("NOVA PROJECT BRAIN DECISION LOG ROUTE CONTRACT SERVICE SMOKE")
    print("============================================================")

    assert_true(
        "extracts message text",
        extract_user_text({"message": "what changed recently"}) == "what changed recently",
    )

    assert_true(
        "matches recent changes",
        is_decision_log_question("what changed recently"),
    )

    assert_true(
        "matches recent decisions",
        is_decision_log_question("show me the recent decisions"),
    )

    assert_true(
        "protects current state recall",
        not is_decision_log_question("what are we working on now"),
    )

    assert_true(
        "protects current blocker recall",
        not is_decision_log_question("what is the current blocker"),
    )

    payload = build_decision_log_api_payload(limit=5)
    answer = payload.get("text", "")
    debug = payload.get("debug", {})

    assert_true("payload ok", payload.get("ok") is True, payload)
    assert_true("payload has answer", "What changed recently:" in answer, answer)
    assert_true("payload has timeline", "Recent Decision Log:" in answer, answer)
    assert_true("payload route", debug.get("route_taken") == "project_brain_general_intelligence", debug)
    assert_true("payload intent", debug.get("intent") == "decision_log", debug)
    assert_true("payload service flag", debug.get("decision_log_route_service") is True, debug)

    print("")
    print("NOVA PROJECT BRAIN DECISION LOG ROUTE CONTRACT SERVICE SMOKE PASSED")


if __name__ == "__main__":
    main()
