from pathlib import Path


ROOT = Path(".")
APP = ROOT / "app.py"
SERVICES = ROOT / "nova_backend" / "services"

RUNTIME_FILES = [
    APP,
    SERVICES / "project_brain_decision_log.py",
    SERVICES / "project_brain_general_intelligence.py",
    SERVICES / "project_brain_mission_control.py",
    SERVICES / "project_brain_freshness_snapshot.py",
    SERVICES / "chat_service.py",
]

SIGNALS = {
    "decision_engine": (
        "decision engine",
        "decision_engine",
        "NOVA_PROJECT_BRAIN_QUESTION_TOP_PRIORITY",
    ),
    "mission_control": (
        "mission control",
        "mission_control",
        "project_brain_mission_control",
    ),
    "failure_interpreter": (
        "failure interpreter",
        "failure_interpreter",
    ),
    "decision_log": (
        "decision log",
        "decision_log",
        "project_brain_decision_log",
        "NOVA_PROJECT_BRAIN_DECISION_LOG",
    ),
}

ROUTE_CONTRACT_SIGNALS = (
    "before_request",
    "route contract",
    "route_taken",
    "project_brain_general_intelligence",
    "project_state_current_memory_direct_recall",
)

AVOID_RULES = (
    "do not add a blind app.py guard",
    "avoid new route-layer patches",
    "move intelligence into services",
)


def read_text(path):
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def find_lines(path, needles):
    text = read_text(path)
    lowered_lines = text.lower().splitlines()
    hits = []

    for index, line in enumerate(lowered_lines, start=1):
        if any(needle.lower() in line for needle in needles):
            hits.append(index)

    return hits


def count_runtime_hits(needles):
    hits = {}

    for path in RUNTIME_FILES:
        if not path.exists():
            continue

        line_hits = find_lines(path, needles)
        if line_hits:
            hits[str(path)] = line_hits

    return hits


def marker_lines(path):
    text = read_text(path)
    lines = []

    for index, line in enumerate(text.splitlines(), start=1):
        lowered = line.lower()
        if (
            "nova_project_brain" in lowered
            or "mission_control" in lowered
            or "failure_interpreter" in lowered
            or "decision_log" in lowered
        ):
            lines.append((index, line.strip()[:140]))

    return lines


def risk_label(count):
    if count >= 40:
        return "high"
    if count >= 18:
        return "medium"
    return "low"


def main():
    print("NOVA PROJECT BRAIN ROUTE PATCH AUDIT SMOKE")
    print("===========================================")

    assert_true("app.py exists", APP.exists(), APP)
    assert_true("services folder exists", SERVICES.exists(), SERVICES)

    print("")
    print("Runtime signal map:")

    all_signal_hits = {}

    for name, needles in SIGNALS.items():
        hits = count_runtime_hits(needles)
        all_signal_hits[name] = hits

        total = sum(len(lines) for lines in hits.values())
        print(f"- {name}: {total} hit(s)")

        for path, lines in hits.items():
            preview = ", ".join(str(line) for line in lines[:12])
            suffix = "..." if len(lines) > 12 else ""
            print(f"  {path}: {preview}{suffix}")

        assert_true(f"{name} runtime signal visible", total >= 1, hits)

    print("")
    print("app.py Project Brain route/guard marker map:")

    app_markers = marker_lines(APP)
    for line_no, line in app_markers[:80]:
        print(f"- line {line_no}: {line}")

    if len(app_markers) > 80:
        print(f"- ... {len(app_markers) - 80} more app.py marker line(s)")

    app_risk = risk_label(len(app_markers))
    print("")
    print(f"app.py Project Brain marker count: {len(app_markers)}")
    print(f"app.py route-layer cleanup risk: {app_risk}")

    assert_true("app.py project brain markers visible", len(app_markers) >= 1)
    assert_true(
        "decision log service exists",
        (SERVICES / "project_brain_decision_log.py").exists(),
    )

    route_hits = count_runtime_hits(ROUTE_CONTRACT_SIGNALS)
    route_total = sum(len(lines) for lines in route_hits.values())

    assert_true("route contract signals visible", route_total >= 1, route_hits)

    avoid_hits = count_runtime_hits(AVOID_RULES)
    avoid_total = sum(len(lines) for lines in avoid_hits.values())

    assert_true("avoid rules visible", avoid_total >= 1, avoid_hits)

    print("")
    print("Recommended cleanup targets:")
    print("- Keep direct project-state recall separate from Mission Control.")
    print("- Keep Decision Log recent-change routing separate from current-state recall.")
    print("- Prefer extracting app.py route hooks into services before adding new guards.")
    print("- Use this audit before any Project Brain cleanup commit.")

    print("")
    print("NOVA PROJECT BRAIN ROUTE PATCH AUDIT SMOKE PASSED")


if __name__ == "__main__":
    main()
