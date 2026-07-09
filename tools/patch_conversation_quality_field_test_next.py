from pathlib import Path

RADAR = Path("nova_backend/services/project_brain_upgrade_radar.py")
SMOKE = Path("tools/nova_conversation_quality_field_test_smoke.py")

radar_text = RADAR.read_text(encoding="utf-8-sig")

if "NOVA_CONVERSATION_QUALITY_FIELD_TEST_NEXT_20260702" not in radar_text:
    block = r'''

# NOVA_CONVERSATION_QUALITY_FIELD_TEST_NEXT_20260702
# After backend stable tag, next best move is lived conversation quality testing.
def get_upgrade_candidates() -> list[UpgradeCandidate]:
    return [
        UpgradeCandidate(
            name="Nova Conversation Quality Field Test v1",
            why=(
                "Backend is stable enough to stop blind surgery and collect real conversation examples "
                "where Nova feels shallow, confused, too bot-like, or loses continuation."
            ),
            risk="low",
            score=220,
            target_files=(
                "tools/nova_conversation_quality_field_test_smoke.py",
                "nova_backend/services/project_brain_upgrade_radar.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_conversation_quality_field_test_smoke.py",
                r"python .\tools\nova_final_response_shape_contract_smoke.py",
                r"python .\tools\nova_regression_smoke.py",
            ),
        ),
        UpgradeCandidate(
            name="App.py Guard Cleanup Pass 2",
            why="Continue removing one small redundant final JSON mutator at a time.",
            risk="medium",
            score=170,
            target_files=(
                "app.py",
                "tools/nova_finalizer_pipeline_audit.py",
                "tools/nova_regression_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_finalizer_pipeline_audit.py",
                r"python .\tools\nova_regression_smoke.py",
            ),
            loses_to_best_because="Conversation quality should be field-tested now that backend is tagged stable.",
        ),
        UpgradeCandidate(
            name="Project Brain State Bridge v1",
            why="Already locked; keep it visible only as completed infrastructure.",
            risk="low",
            score=80,
            target_files=(
                "nova_backend/services/project_brain_state_bridge.py",
                "tools/nova_project_brain_state_bridge_smoke.py",
            ),
            focused_smokes=(
                r"python .\tools\nova_project_brain_state_bridge_smoke.py",
            ),
            loses_to_best_because="Already completed and stable-tagged.",
        ),
    ]


def select_best_upgrade() -> UpgradeCandidate:
    candidates = get_upgrade_candidates()
    return sorted(candidates, key=lambda item: item.score, reverse=True)[0]


def build_upgrade_radar_summary() -> str:
    candidates = get_upgrade_candidates()
    lines = ["Project Brain Upgrade Radar:"]
    for index, candidate in enumerate(sorted(candidates, key=lambda item: item.score, reverse=True), start=1):
        lines.append(f"{index}. {candidate.name} — {candidate.why}")
    return "\n".join(lines)
'''
    RADAR.write_text(radar_text.rstrip() + "\n" + block + "\n", encoding="utf-8")
    print("patched Upgrade Radar to rank Conversation Quality Field Test next")
else:
    print("Conversation Quality Field Test ranking already installed")

SMOKE.write_text(r'''
import time
import requests

BASE = "http://127.0.0.1:5001"


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def post_chat(message, session_id):
    response = requests.post(
        f"{BASE}/api/chat",
        json={
            "message": message,
            "session_id": session_id,
            "attachments": [],
        },
        timeout=30,
    )
    assert_true(f"{message} status", response.status_code == 200, response.text[:800])
    return response.json()


def get_text(data):
    assistant = data.get("assistant_message")
    assistant_text = ""
    if isinstance(assistant, dict):
        assistant_text = assistant.get("text") or assistant.get("content") or ""

    return (
        data.get("text")
        or data.get("answer")
        or data.get("message")
        or assistant_text
        or ""
    )


def get_route(data):
    debug = data.get("debug") if isinstance(data.get("debug"), dict) else {}
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    assistant = data.get("assistant_message") if isinstance(data.get("assistant_message"), dict) else {}
    assistant_meta = assistant.get("meta") if isinstance(assistant.get("meta"), dict) else {}

    return (
        data.get("route")
        or data.get("route_taken")
        or debug.get("route_taken")
        or debug.get("route")
        or meta.get("route")
        or meta.get("strategy")
        or assistant_meta.get("route")
        or assistant_meta.get("strategy")
        or ""
    )


def assert_usable_answer(name, data):
    text = get_text(data)
    assert_true(f"{name} has text", bool(text.strip()), data)
    assert_true(f"{name} has assistant message", isinstance(data.get("assistant_message"), dict), data)
    assert_true(f"{name} has debug", isinstance(data.get("debug"), dict), data)


def main():
    print("NOVA CONVERSATION QUALITY FIELD TEST SMOKE")
    print("==========================================")

    stamp = str(int(time.time()))
    session_id = f"conversation_quality_{stamp}"

    first = post_chat("hey nova", session_id)
    assert_usable_answer("casual greeting", first)
    assert_true("casual greeting not execution", "execution" not in get_route(first).lower(), first)

    second = post_chat("i'm testing if you can keep following what i'm saying", session_id)
    assert_usable_answer("continuation setup", second)
    assert_true("continuation setup not image", "image" not in get_route(second).lower(), second)

    direct = post_chat("what are we working on now", session_id)
    assert_usable_answer("direct project recall", direct)
    assert_true("direct recall route", get_route(direct) == "project_state_current_memory_direct_recall", direct)
    assert_true("direct recall fresh next move", "Project Brain State Recall Refresh v1" in get_text(direct), get_text(direct))

    general = post_chat("what changed recently in the Nova project", session_id)
    assert_usable_answer("general project answer", general)
    assert_true("general project route", get_route(general) == "project_brain_general_intelligence", general)

    print("")
    print("NOVA CONVERSATION QUALITY FIELD TEST SMOKE PASSED")


if __name__ == "__main__":
    main()
''', encoding="utf-8")

print("installed Conversation Quality Field Test v1")
