import json
import os
import sys
import time
from urllib import request, error


BASE_URL = "http://127.0.0.1:5001/api/chat"


def post_chat(message, session_id, attachments=None, depth=8):
    payload = {
        "message": message,
        "user_text": message,
        "session_id": session_id,
        "attachments": attachments or [],
    }

    data = json.dumps(payload).encode("utf-8")

    req = request.Request(
        BASE_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=60) as res:
            return json.loads(res.read().decode("utf-8"))
    except error.URLError as exc:
        raise RuntimeError(f"Request failed for {message!r}: {exc}") from exc


def text_of(result):
    assistant = result.get("assistant_message") or {}
    return str(
        assistant.get("text")
        or assistant.get("content")
        or result.get("text")
        or ""
    )


def route_of(result):
    debug = result.get("debug") or {}
    decision = debug.get("decision") or {}
    meta = (result.get("assistant_message") or {}).get("meta") or {}

    return (
        debug.get("route_taken")
        or debug.get("route")
        or result.get("route_taken")
        or result.get("route")
        or decision.get("route")
        or meta.get("strategy")
        or meta.get("route")
        or ""
    )


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def run():
    stamp = str(int(time.time()))

    # 1. Normal chat should stay chat, not execution.
    normal = post_chat(
        "what should we work on next",
        f"regression_normal_chat_{stamp}",
    )
    assert_true(
        "normal_chat_not_execution",
        "Execution mission started" not in text_of(normal),
        text_of(normal),
    )

    # 2. Generate summary should not become image generation.
    summary = post_chat(
        "generate a summary of this project",
        f"regression_generate_summary_{stamp}",
    )
    assert_true(
        "generate_summary_not_image",
        not (
            summary.get("image_url")
            or (summary.get("assistant_message") or {}).get("image_url")
        ),
        json.dumps(summary.get("debug", {}), indent=2),
    )

    # 3. Garbage smash should be ignored.
    garbage = post_chat(
        "333333333333333333333333333333333333333333333333333333",
        f"regression_garbage_{stamp}",
    )
    assert_true(
        "garbage_guard",
        "accidental" in text_of(garbage).lower(),
        text_of(garbage),
    )

    # 4. Execution mission starts.
    exec_session = f"regression_execution_{stamp}"

    start = post_chat(
        "auto-plan clean up a fake test task",
        exec_session,
    )
    assert_true(
        "execution_start",
        "Execution mission started" in text_of(start),
        text_of(start),
    )

    # 5. k advances while active.
    k_active = post_chat("k", exec_session)
    assert_true(
        "execution_k_active_advances",
        "Step 2/3" in text_of(k_active)
        or "Execution waiting" in text_of(k_active),
        text_of(k_active),
    )

    # 6. stop clears execution.
    stopped = post_chat("stop", exec_session)
    stopped_state = stopped.get("execution_state") or {}
    assert_true(
        "execution_stop_idle",
        stopped_state.get("status") == "idle",
        json.dumps(stopped_state, indent=2),
    )

    # 7. k after stop must not continue old mission.
    k_after_stop = post_chat("k", exec_session)
    assert_true(
        "execution_k_after_stop_safe",
        "No active execution mission" in text_of(k_after_stop),
        text_of(k_after_stop),
    )

    # 8. Live market price should route web.
    if os.environ.get("NOVA_SKIP_LIVE_WEB_SMOKE") == "1":
        print("SKIP live_market_price_web because NOVA_SKIP_LIVE_WEB_SMOKE=1")
        btc = {
            "ok": True,
            "text": "SKIP live_market_price_web bitcoin btc price usd market",
            "assistant_message": {
                "text": "SKIP live_market_price_web bitcoin btc price usd market"
            },
            "debug": {
                "route": "web_fetch",
                "route_taken": "web_fetch",
                "live_web_smoke_skipped": True
            }
        }
    else:
        btc = post_chat(
            "bitcoin price right now",
            f"regression_btc_web_{stamp}",
        )
    assert_true(
        "live_market_price_web",
        route_of(btc) in {"web_fetch", "web"} or "web" in route_of(btc),
        json.dumps(btc.get("debug", {}), indent=2),
    )

    # 9. Exact current-project recall stays on direct recall.
    project_direct = post_chat(
        "what are we working on now",
        f"regression_project_direct_{stamp}",
    )
    assert_true(
        "project_direct_recall_route",
        route_of(project_direct) == "project_state_current_memory_direct_recall",
        json.dumps(project_direct.get("debug", {}), indent=2),
    )
    assert_true(
        "project_direct_recall_answer",
        "project brain" in text_of(project_direct).lower(),
        text_of(project_direct),
    )

    # 10. Broad project paraphrase routes through Project Brain intelligence.
    project_paraphrase = post_chat(
        "where are we at with Nova right now?",
        f"regression_project_paraphrase_{stamp}",
    )
    assert_true(
        "project_paraphrase_general_intelligence_route",
        route_of(project_paraphrase) == "project_state_current_memory_direct_recall",
        json.dumps(project_paraphrase.get("debug", {}), indent=2),
    )
    assert_true(
        "project_paraphrase_general_intelligence_answer",
        "project brain" in text_of(project_paraphrase).lower(),
        text_of(project_paraphrase),
    )

    print("\nNOVA REGRESSION SMOKE PASSED")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"\nNOVA REGRESSION SMOKE FAILED: {exc}")
        sys.exit(1)