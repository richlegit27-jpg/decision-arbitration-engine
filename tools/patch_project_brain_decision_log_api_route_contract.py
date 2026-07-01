from pathlib import Path


TARGET = Path("app.py")
MARKER = "NOVA_PROJECT_BRAIN_DECISION_LOG_API_ROUTE_CONTRACT_20260701"

if not TARGET.exists():
    raise SystemExit("missing app.py")

text = TARGET.read_text(encoding="utf-8-sig")

if MARKER in text:
    print("Decision Log API route contract already installed")
    raise SystemExit(0)

patch = r'''


# NOVA_PROJECT_BRAIN_DECISION_LOG_API_ROUTE_CONTRACT_20260701
# Narrow route contract for Project Brain Decision Log questions.
# Keeps current-state/project-state recall separate.
try:
    from flask import request, jsonify
    from nova_backend.services.project_brain_decision_log import answer_recent_changes as _nova_decision_log_answer_20260701

    _NOVA_DECISION_LOG_ROUTE_KEYWORDS_20260701 = (
        "what changed recently",
        "what changed lately",
        "recent changes",
        "recent decisions",
        "decision log",
        "recent commits",
        "last commits",
        "latest commits",
        "what did we commit",
        "what did we lock recently",
        "what got locked recently",
        "locked upgrades",
        "operator timeline",
    )

    def _nova_decision_log_api_text_20260701():
        try:
            data = request.get_json(silent=True) or {}
        except Exception:
            data = {}

        for key in ("message", "question", "user_text", "text", "prompt"):
            value = data.get(key)
            if isinstance(value, str):
                return value

        return ""

    def _nova_is_decision_log_api_question_20260701(user_text):
        text = str(user_text or "").strip().lower()
        if not text:
            return False

        # Preserve direct project-state recall/current blocker routes.
        protected_direct_recall = (
            "what are we working on",
            "what are we doing now",
            "current project state",
            "current blocker",
            "what is the blocker",
            "what should we do next",
        )
        if any(needle in text for needle in protected_direct_recall):
            return False

        return any(needle in text for needle in _NOVA_DECISION_LOG_ROUTE_KEYWORDS_20260701)

    @app.before_request
    def _nova_project_brain_decision_log_api_route_contract_20260701():
        try:
            if request.path != "/api/chat" or request.method != "POST":
                return None

            user_text = _nova_decision_log_api_text_20260701()
            if not _nova_is_decision_log_api_question_20260701(user_text):
                return None

            answer = _nova_decision_log_answer_20260701(limit=8)

            return jsonify({
                "ok": True,
                "text": answer,
                "assistant_message": {
                    "role": "assistant",
                    "text": answer,
                    "content": answer,
                    "attachments": [],
                },
                "debug": {
                    "route": "project_brain_general_intelligence",
                    "route_taken": "project_brain_general_intelligence",
                    "intent": "decision_log",
                    "decision_log_route_contract": True,
                },
            })
        except Exception as exc:
            try:
                print("[NOVA_PROJECT_BRAIN_DECISION_LOG_API_ROUTE_CONTRACT_20260701] failed:", exc)
            except Exception:
                pass
            return None

    print("[NOVA_PROJECT_BRAIN_DECISION_LOG_API_ROUTE_CONTRACT_20260701] installed")
except Exception as _nova_decision_log_api_route_error_20260701:
    print("[NOVA_PROJECT_BRAIN_DECISION_LOG_API_ROUTE_CONTRACT_20260701] failed:", _nova_decision_log_api_route_error_20260701)
'''

TARGET.write_text(text + patch, encoding="utf-8")
print("installed Decision Log API route contract in app.py")
