from nova_backend.services.project_brain_decision_log import (
    answer_recent_changes,
    format_decision_timeline,
    get_recent_decisions,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    decisions = get_recent_decisions(limit=12)
    timeline = format_decision_timeline(limit=8)
    answer = answer_recent_changes(limit=8)

    blob = (timeline + "\n" + answer).lower()

    assert_true("decision log returns list", isinstance(decisions, list))
    assert_true("decision log has entries", len(decisions) >= 1, decisions)
    assert_true("decision entries have hash", bool(decisions[0].get("short_hash")), decisions[0])
    assert_true("decision entries have subject", bool(decisions[0].get("subject")), decisions[0])
    assert_true("timeline labels recent decisions", "recent decision log:" in blob)
    assert_true("answer labels recent changes", "what changed recently:" in blob)
    assert_true("operator timeline protected", "operator timeline" in blob)
    assert_true("direct recall protected", "direct project-state recall remains" in blob)

    assert_true(
        "failure interpreter appears in recent decisions",
        "failure interpreter" in blob,
        timeline,
    )

    print("")
    print("PROJECT BRAIN DECISION LOG SMOKE PASSED")


if __name__ == "__main__":
    main()
