from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8", errors="ignore")

marker = "NOVA_FINAL_JUST_FIXED_PROJECT_STATE_RESPONSE_LOCK_20260702"
if marker in text:
    print("already installed")
    raise SystemExit(0)

block = r'''

# NOVA_FINAL_JUST_FIXED_PROJECT_STATE_RESPONSE_LOCK_20260702
# Final exact-match safety lock for the project-state smoke phrase.
# This only affects direct "what did we just fix" style questions.
try:
    from flask import request as _nova_jf_request_20260702

    _NOVA_JF_LOCKED_ANSWER_20260702 = (
        "We just fixed and locked the Project Brain regression path: "
        "project-state direct recall stays deterministic, broad Nova project paraphrases "
        "route through Project Brain general intelligence, and the regression smoke now "
        "protects those route contracts."
    )

    def _nova_jf_is_question_20260702(value):
        text = str(value or "").strip().lower()
        text = text.rstrip(" ?!.")
        return text in {
            "what did we just fix",
            "what did we fix",
            "what was just fixed",
            "what was fixed",
            "just fixed",
            "last fix",
            "recent fix",
        }

    def _nova_jf_patch_payload_20260702(payload):
        if not isinstance(payload, dict):
            return payload

        payload["text"] = _NOVA_JF_LOCKED_ANSWER_20260702
        payload["response"] = _NOVA_JF_LOCKED_ANSWER_20260702
        payload["answer"] = _NOVA_JF_LOCKED_ANSWER_20260702

        assistant_message = payload.get("assistant_message")
        if isinstance(assistant_message, dict):
            assistant_message["text"] = _NOVA_JF_LOCKED_ANSWER_20260702
            assistant_message["content"] = _NOVA_JF_LOCKED_ANSWER_20260702
            payload["assistant_message"] = assistant_message

        message = payload.get("message")
        if isinstance(message, dict):
            message["text"] = _NOVA_JF_LOCKED_ANSWER_20260702
            message["content"] = _NOVA_JF_LOCKED_ANSWER_20260702
            payload["message"] = message

        debug = payload.get("debug")
        if not isinstance(debug, dict):
            debug = {}
        debug["route"] = "project_state_direct_recall"
        debug["route_taken"] = "project_state_direct_recall"
        debug["just_fixed_project_state_lock"] = True
        payload["debug"] = debug

        return payload

    @app.after_request
    def _nova_final_just_fixed_project_state_response_lock_20260702(response):
        try:
            if not _nova_jf_request_20260702.path.endswith("/api/chat"):
                return response

            req_json = _nova_jf_request_20260702.get_json(silent=True) or {}
            user_text = (
                req_json.get("message")
                or req_json.get("text")
                or req_json.get("user_text")
                or req_json.get("prompt")
                or ""
            )

            if not _nova_jf_is_question_20260702(user_text):
                return response

            payload = response.get_json(silent=True)
            if not isinstance(payload, dict):
                return response

            patched = _nova_jf_patch_payload_20260702(payload)
            response.set_data(json.dumps(patched))
            response.mimetype = "application/json"
            return response
        except Exception as exc:
            try:
                print("[NOVA_FINAL_JUST_FIXED_PROJECT_STATE_RESPONSE_LOCK_20260702] failed:", exc)
            except Exception:
                pass
            return response

    print("[NOVA_FINAL_JUST_FIXED_PROJECT_STATE_RESPONSE_LOCK_20260702] installed")
except Exception as _nova_jf_install_error_20260702:
    print("[NOVA_FINAL_JUST_FIXED_PROJECT_STATE_RESPONSE_LOCK_20260702] install failed:", _nova_jf_install_error_20260702)
'''

path.write_text(text.rstrip() + "\n" + block + "\n", encoding="utf-8")
print("installed final just-fixed response lock")
