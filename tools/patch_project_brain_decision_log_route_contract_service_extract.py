from pathlib import Path
import re


TARGET = Path("app.py")
MARKER = "NOVA_PROJECT_BRAIN_DECISION_LOG_API_ROUTE_CONTRACT_20260701"

if not TARGET.exists():
    raise SystemExit("missing app.py")

text = TARGET.read_text(encoding="utf-8-sig")

pattern = re.compile(
    r"\n*# NOVA_PROJECT_BRAIN_DECISION_LOG_API_ROUTE_CONTRACT_20260701"
    r".*?"
    r"print\(\s*\"\[NOVA_PROJECT_BRAIN_DECISION_LOG_API_ROUTE_CONTRACT_20260701\] failed:\",\s*_nova_decision_log_api_route_error_20260701\s*\)\n?",
    re.DOTALL,
)

match = pattern.search(text)
if not match:
    raise SystemExit("could not isolate existing Decision Log API route contract block")

replacement = r'''


# NOVA_PROJECT_BRAIN_DECISION_LOG_API_ROUTE_CONTRACT_20260701
# Thin Flask wrapper for the service-owned Decision Log route contract.
# Keeps current-state/project-state recall separate.
try:
    from flask import request, jsonify
    from nova_backend.services.project_brain_decision_log_route_contract import (
        build_decision_log_api_payload as _nova_build_decision_log_api_payload_20260701,
        extract_user_text as _nova_decision_log_extract_user_text_20260701,
        is_decision_log_question as _nova_is_decision_log_api_question_20260701,
    )

    @app.before_request
    def _nova_project_brain_decision_log_api_route_contract_20260701():
        try:
            if request.path != "/api/chat" or request.method != "POST":
                return None

            try:
                payload = request.get_json(silent=True) or {}
            except Exception:
                payload = {}

            user_text = _nova_decision_log_extract_user_text_20260701(payload)
            if not _nova_is_decision_log_api_question_20260701(user_text):
                return None

            return jsonify(_nova_build_decision_log_api_payload_20260701(limit=8))
        except Exception as exc:
            try:
                print("[NOVA_PROJECT_BRAIN_DECISION_LOG_API_ROUTE_CONTRACT_20260701] failed:", exc)
            except Exception:
                pass
            return None

    print("[NOVA_PROJECT_BRAIN_DECISION_LOG_API_ROUTE_CONTRACT_20260701] installed service wrapper")
except Exception as _nova_decision_log_api_route_error_20260701:
    print("[NOVA_PROJECT_BRAIN_DECISION_LOG_API_ROUTE_CONTRACT_20260701] failed:", _nova_decision_log_api_route_error_20260701)
'''

new_text = text[:match.start()] + replacement + text[match.end():]
TARGET.write_text(new_text, encoding="utf-8")

print("replaced app.py Decision Log API route contract with service wrapper")
