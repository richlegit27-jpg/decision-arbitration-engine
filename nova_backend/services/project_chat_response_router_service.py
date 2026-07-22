import json
import importlib.util
from pathlib import Path

# NOVA_API_CHAT_PROJECT_STATE_IDLE_NEXT_FINAL_20260630
# Final /api/chat response repair for idle next/k project-state recall.
# This runs at the Flask route layer because the idle execution fallback is produced
# outside ChatService.handle in some paths.

try:
    import json as _nova_api_project_state_json_20260630
    import importlib.util as _nova_api_project_state_importlib_util_20260630
    from pathlib import Path as _NovaApiProjectStatePath20260630
    from flask import request as _nova_api_project_state_request_20260630

    def _nova_api_project_state_load_answer_20260630(user_text):
        service_path = (
            _NovaApiProjectStatePath20260630(__file__)
            .resolve()
            .parent
            / "nova_backend"
            / "services"
            / "project_state_service.py"
        )

        spec = _nova_api_project_state_importlib_util_20260630.spec_from_file_location(
            "_nova_api_project_state_service_direct_20260630",
            str(service_path),
        )

        if not spec or not spec.loader:
            return None

        module = _nova_api_project_state_importlib_util_20260630.module_from_spec(spec)
        spec.loader.exec_module(module)

        answer_fn = getattr(module, "answer_project_state_question", None)
        if not callable(answer_fn):
            return None

        return answer_fn(user_text, runtime_execution_state=None)

    def _nova_api_project_state_patch_payload_20260630(payload, reply):
        if not isinstance(payload, dict):
            payload = {}

        payload["ok"] = True
        payload["success"] = True
        payload["content"] = reply
        payload["message"] = reply
        payload["response"] = reply
        payload["route"] = "project_state_recall"
        payload["route_taken"] = "project_state_recall"

        assistant = payload.get("assistant_message")
        if not isinstance(assistant, dict):
            assistant = {
                "role": "assistant",
                "attachments": [],
            }

        assistant["content"] = reply
        assistant.setdefault("role", "assistant")
        assistant.setdefault("attachments", [])
        payload["assistant_message"] = assistant

        debug = payload.get("debug")
        if not isinstance(debug, dict):
            debug = {}
        debug["route"] = "project_state_recall"
        debug["route_taken"] = "project_state_recall"
        payload["debug"] = debug

        meta = payload.get("meta")
        if not isinstance(meta, dict):
            meta = {}
        meta["route"] = "project_state_recall"
        meta["strategy"] = "project_state_recall"
        payload["meta"] = meta

        return payload

    def _nova_api_project_state_content_20260630(payload):
        if not isinstance(payload, dict):
            return ""

        assistant = payload.get("assistant_message")
        if isinstance(assistant, dict):
            content = assistant.get("content")
            if isinstance(content, str):
                return content

        for key in ("content", "response", "message", "text", "answer"):
            value = payload.get(key)
            if isinstance(value, str):
                return value

        return ""

    def _nova_api_project_state_request_text_20260630():
        try:
            data = _nova_api_project_state_request_20260630.get_json(silent=True) or {}
            if isinstance(data, dict):
                for key in ("message", "user_text", "text", "prompt"):
                    value = data.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
        except Exception:
            pass

        return ""

    def _nova_api_project_state_wrap_endpoint_20260630(app, endpoint_name):
        view = app.view_functions.get(endpoint_name)
        if not callable(view):
            return False

        if getattr(view, "_NOVA_API_CHAT_PROJECT_STATE_IDLE_NEXT_FINAL_20260630", False):
            return True

        def _nova_api_project_state_wrapped_view_20260630(*args, **kwargs):
            result = view(*args, **kwargs)

            try:
                user_text = _nova_api_project_state_request_text_20260630().lower()
                if user_text not in {"next", "k", "ok", "okay", "continue"}:
                    return result

                if not hasattr(result, "get_data") or not hasattr(result, "set_data"):
                    return result

                raw = result.get_data(as_text=True)
                payload = _nova_api_project_state_json_20260630.loads(raw)

                content = _nova_api_project_state_content_20260630(payload)
                if "no active execution mission" not in str(content or "").lower():
                    return result

                reply = _nova_api_project_state_load_answer_20260630(user_text)
                if not reply:
                    return result

                payload = _nova_api_project_state_patch_payload_20260630(payload, reply)
                encoded = _nova_api_project_state_json_20260630.dumps(payload, ensure_ascii=False)

                result.set_data(encoded)
                try:
                    result.headers["Content-Length"] = str(len(result.get_data()))
                    result.headers["Content-Type"] = "application/json"
                except Exception:
                    pass

                return result
            except Exception as _nova_api_project_state_route_error_20260630:
                try:
                    print(
                        "[NOVA_API_CHAT_PROJECT_STATE_IDLE_NEXT_FINAL_20260630] bypass:",
                        _nova_api_project_state_route_error_20260630,
                    )
                except Exception:
                    pass

            return result

        _nova_api_project_state_wrapped_view_20260630.__name__ = getattr(
            view,
            "__name__",
            "_nova_api_project_state_wrapped_view_20260630",
        )
        _nova_api_project_state_wrapped_view_20260630._NOVA_API_CHAT_PROJECT_STATE_IDLE_NEXT_FINAL_20260630 = True

        app.view_functions[endpoint_name] = _nova_api_project_state_wrapped_view_20260630
        return True

except Exception as _nova_api_project_state_install_error_20260630:
    try:
        print(
            "[NOVA_API_CHAT_PROJECT_STATE_IDLE_NEXT_FINAL_20260630] failed:",
            _nova_api_project_state_install_error_20260630,
        )
    except Exception:
        pass

# NOVA_PHASE_7B_LOCAL_UNRESOLVED_RECALL_ROUTE_PRIORITY_20260711
def _nova_phase7b_is_local_unresolved_recall_20260711(value):
    text = " ".join(
        str(value or "")
        .strip()
        .lower()
        .replace("?", "'")
        .split()
    )

    if not text:
        return False

    exact_prompts = {
        "what was the other thing we still needed to do",
        "what was the other thing we needed to do",
        "what was the other thing",
        "what did we say we would do later",
        "what did we say we'd do later",
        "what were we going to come back to",
        "what did we leave for later",
    }

    if text in exact_prompts:
        return True

    local_recall_markers = (
        "the other thing",
        "we said we'd",
        "we said we would",
        "come back to",
        "left for later",
        "put off until later",
        "deferred earlier",
    )

    return any(
        marker in text
        for marker in local_recall_markers
    )


# NOVA_API_CHAT_NATURAL_PROJECT_RECALL_20260701
# Route-level natural project-state recall.
# This intentionally does not modify project_state_service.py.
# It maps short natural project prompts to the already-green project-state answers.
try:
    import json as _nova_natural_project_json_20260701
    import re as _nova_natural_project_re_20260701
    import importlib.util as _nova_natural_project_importlib_util_20260701
    from pathlib import Path as _NovaNaturalProjectPath20260701
    from flask import request as _nova_natural_project_request_20260701
    from flask import Response as _NovaNaturalProjectResponse20260701

    def _nova_natural_project_normalize_20260701(value):
        text = str(value or "").strip().lower()
        text = text.replace("’", "'")
        text = _nova_natural_project_re_20260701.sub(r"\s+", " ", text)
        return text

    def _nova_natural_project_prompt_map_20260701(user_text):
        text = _nova_natural_project_normalize_20260701(user_text)

        if not text or len(text) > 140:
            return ""

        current_exact = {
            "are we good",
            "are we good?",
            "are we locked",
            "are we locked?",
            "is it locked",
            "is it locked?",
            "are we clean",
            "are we clean?",
            "how far are we",
            "how far are we?",
            "how far are we now",
            "how far are we now?",
            "where are we at",
            "where are we at?",
            "where are we now",
            "where are we now?",
            "how close are we",
            "how close are we?",
            "status now",
            "progress now",
            "what are we working on",
            "what are we working on?",
            "what are we working on now",
            "what are we working on now?",
            "what are we working on right now",
            "what are we working on right now?",
        }

        fixed_exact = {
            "what is locked",
            "what is locked?",
            "what's locked",
            "what's locked?",
            "what got locked",
            "what got locked?",
            "what did we lock",
            "what did we lock?",
            "what passed",
            "what passed?",
            "what is green",
            "what is green?",
            "what's green",
            "what's green?",
        }

        remaining_exact = {
            "anything left",
            "anything left?",
            "anything else",
            "anything else?",
            "what else",
            "what else?",
            "what still needs doing",
            "what still needs doing?",
            "what needs doing",
            "what needs doing?",
            "how much is left",
            "how much is left?",
        }

        next_exact = {
            "what should we do now",
            "what should we do now?",
            "what do we do now",
            "what do we do now?",
            "what now",
            "what now?",
            "can we move on",
            "can we move on?",
            "should we move on",
            "should we move on?",
            "move on?",
        }

        if text in current_exact:
            return ""

        if text in fixed_exact:
            return "what did we just fix?"

        if text in remaining_exact:
            return ""

        if text in next_exact:
            return "next"

        return ""
    def _nova_natural_project_request_json_20260701():
        try:
            data = _nova_natural_project_request_20260701.get_json(silent=True) or {}
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _nova_natural_project_request_text_20260701(data):
        for key in ("message", "user_text", "text", "prompt"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _nova_natural_project_load_answer_20260701(mapped_prompt):
        try:
            from nova_backend.services.project_brain_general_intelligence import (
                build_project_brain_general_answer,
            )

            answer = build_project_brain_general_answer(
                mapped_prompt
            )

            if hasattr(answer, "text"):
                return answer.text

            if isinstance(answer, str):
                return answer

        except Exception as error:
            try:
                print(
                    "[NOVA_NATURAL_PROJECT_LOAD_GENERAL_BRAIN_FAILED]",
                    error,
                )
            except Exception:
                pass

        return None

    def _nova_natural_project_payload_20260701(reply, data):
        session_id = ""
        if isinstance(data, dict):
            session_id = str(data.get("session_id") or data.get("active_session_id") or "").strip()

        payload = {
            "ok": True,
            "success": True,
            "content": reply,
            "message": reply,
            "response": reply,
            "session_id": session_id,
            "active_session_id": session_id,
            "assistant_message": {
                "role": "assistant",
                "content": reply,
                "text": reply,
                "attachments": [],
            },
            "route": "project_brain_general_intelligence",
            "route_taken": "project_brain_general_intelligence",
            "debug": {
                "route": "project_brain_general_intelligence",
                "route_taken": "project_brain_general_intelligence",
                "natural_project_recall": True,
            },
            "meta": {
                "route": "project_brain_general_intelligence",
                "strategy": "project_brain_general_intelligence",
            },
        }
        return payload

    def _nova_natural_project_wrap_endpoint_20260701(app, endpoint_name):
        view = app.view_functions.get(endpoint_name)
        if not callable(view):
            return False

        if getattr(view, "_NOVA_API_CHAT_NATURAL_PROJECT_RECALL_20260701", False):
            return True

        def _nova_natural_project_wrapped_view_20260701(*args, **kwargs):
            try:
                data = _nova_natural_project_request_json_20260701()
                user_text = _nova_natural_project_request_text_20260701(data)

                if _nova_phase7b_is_local_unresolved_recall_20260711(
                    user_text
                ):
                    return view(
                        *args,
                        **kwargs,
                    )
                mapped_prompt = _nova_natural_project_prompt_map_20260701(user_text)

                if mapped_prompt:
                    reply = _nova_natural_project_load_answer_20260701(mapped_prompt)
                    if reply:
                        payload = _nova_natural_project_payload_20260701(reply, data)
                        encoded = _nova_natural_project_json_20260701.dumps(payload, ensure_ascii=False)
                        return _NovaNaturalProjectResponse20260701(
                            encoded,
                            status=200,
                            mimetype="application/json",
                        )
            except Exception as _nova_natural_project_route_error_20260701:
                try:
                    print(
                        "[NOVA_API_CHAT_NATURAL_PROJECT_RECALL_20260701] bypass:",
                        _nova_natural_project_route_error_20260701,
                    )
                except Exception:
                    pass

            return view(*args, **kwargs)

        _nova_natural_project_wrapped_view_20260701.__name__ = getattr(
            view,
            "__name__",
            "_nova_natural_project_wrapped_view_20260701",
        )
        _nova_natural_project_wrapped_view_20260701._NOVA_API_CHAT_NATURAL_PROJECT_RECALL_20260701 = True

        app.view_functions[endpoint_name] = _nova_natural_project_wrapped_view_20260701
        return True

except Exception as _nova_natural_project_install_error_20260701:
    try:
        print(
            "[NOVA_API_CHAT_NATURAL_PROJECT_RECALL_20260701] failed:",
            _nova_natural_project_install_error_20260701,
        )
    except Exception:
        pass


# NOVA_API_CHAT_COMPACT_PROJECT_CONTEXT_20260701

# Route-level compact project-state context for broader Nova/project status prompts.
# Uses project_state_service.compact_project_state_context() but does not modify the service.
try:
    import json as _nova_compact_project_json_20260701
    import re as _nova_compact_project_re_20260701
    import importlib.util as _nova_compact_project_importlib_util_20260701
    from pathlib import Path as _NovaCompactProjectPath20260701
    from flask import request as _nova_compact_project_request_20260701
    from flask import Response as _NovaCompactProjectResponse20260701

    def _nova_compact_project_normalize_20260701(value):
        text = str(value or "").strip().lower()
        text = text.replace("’", "'")
        text = _nova_compact_project_re_20260701.sub(r"\s+", " ", text)
        return text

    def _nova_compact_project_should_answer_20260701(user_text):
        text = _nova_compact_project_normalize_20260701(user_text)

        if not text or len(text) > 240:
            return False

        # Leave exact direct commands to the already-locked project-state/natural-recall wrappers.
        exact_owned_elsewhere = {
            "what are we working on",
            "what are we working on?",
            "what did we just fix",
            "what did we just fix?",
            "what is left",
            "what is left?",
            "next",
            "k",
            "are we good",
            "are we good?",
            "what is locked",
            "what is locked?",
            "how far are we now",
            "how far are we now?",
            "what should we do now",
            "what should we do now?",
            "can we move on",
            "can we move on?",
        }

        if text in exact_owned_elsewhere:
            return False

        project_terms = [
            "nova",
            "project",
            "checkpoint",
            "current work",
            "our work",
            "what we're doing",
            "what we are doing",
            "what nova remembers",
            "what nova is actively doing",
            "separate what nova remembers",
            "memory from execution",
            "remembered from active",
        ]

        status_terms = [
            "status",
            "summary",
            "context",
            "checkpoint",
            "progress",
            "phase",
            "execution",
            "memory",
        ]

        has_project_term = any(term in text for term in project_terms)
        has_status_term = any(term in text for term in status_terms)

        blocked_terms = [
            "bitcoin",
            "price",
            "weather",
            "image",
            "generate image",
            "draw",
            "attachment",
            "upload",
            "file",
            "soccer",
            "news",
        ]

        if any(term in text for term in blocked_terms):
            return False

        return has_project_term and has_status_term

    def _nova_compact_project_request_json_20260701():
        try:
            data = _nova_compact_project_request_20260701.get_json(silent=True) or {}
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _nova_compact_project_request_text_20260701(data):
        for key in ("message", "user_text", "text", "prompt"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _nova_compact_project_brain_response_20260701(
        user_text,
    ):
        # NOVA_COMPACT_PROJECT_CONTEXT_DELEGATE_TO_PROJECT_BRAIN_20260701
        # Broad Nova project paraphrases belong to Project Brain
        # general intelligence.
        try:
            normalized = (
                _nova_compact_project_normalize_20260701(
                    user_text
                )
            )

            # -------------------------------------------------
            # EXPLICIT COMMAND REGISTRY OWNS ITS COMMAND PREFIX.
            # -------------------------------------------------

            if normalized.startswith(
                "command-registry:"
            ):
                return None

            # -------------------------------------------------
            # ACTIVE EXECUTION OWNS EXECUTION CONTROL WORDS.
            #
            # This compact Project Brain delegate is a second
            # Project Brain interception path. It must yield the
            # exact execution-control words Nova advertises when
            # an active mission exists.
            # -------------------------------------------------

            execution_controls = {
                "k",
                "next",
                "continue",
                "run it",
            }

            if normalized in execution_controls:

                request_data = (
                    _nova_compact_project_request_json_20260701()
                )

                session_id = str(
                    request_data.get(
                        "session_id"
                    )
                    or request_data.get(
                        "active_session_id"
                    )
                    or request_data.get(
                        "requested_session_id"
                    )
                    or ""
                ).strip()

                active_execution_getter = globals().get(
                    "_nova_phase4a_get_active_execution_20260701"
                )

                execution_is_active = globals().get(
                    "_nova_phase4a_execution_is_active_20260701"
                )

                if (
                    callable(
                        active_execution_getter
                    )
                    and callable(
                        execution_is_active
                    )
                ):

                    try:
                        active_execution = (
                            active_execution_getter(
                                session_id
                            )
                        )

                    except Exception as exc:
                        active_execution = None

                        try:
                            print(
                                "[NOVA_COMPACT_PROJECT_CONTEXT_DELEGATE_TO_PROJECT_BRAIN_20260701] "
                                "active execution control bypass:",
                                exc,
                            )
                        except Exception:
                            pass

                    if (
                        isinstance(
                            active_execution,
                            dict,
                        )
                        and execution_is_active(
                            active_execution
                        )
                    ):
                        return None

            direct_recall_prompts = {
                "what are we working on",
                "what are we working on?",
                "what are we working on now",
                "what are we working on now?",
                "what are we working on right now",
                "what are we working on right now?",
            }

            if normalized in direct_recall_prompts:
                return None

            from nova_backend.services.project_brain_general_intelligence import (
                build_project_brain_general_answer,
            )

            answer = (
                build_project_brain_general_answer(
                    user_text
                )
            )

            if not answer:
                return None

            answer_text = str(
                getattr(
                    answer,
                    "text",
                    answer,
                )
                or ""
            ).strip()

            answer_intent = str(
                getattr(
                    answer,
                    "intent",
                    "general_project_answer",
                )
                or "general_project_answer"
            ).strip()

            if not answer_text:
                return None

            return _NovaCompactProjectResponse20260701(
                _nova_compact_project_json_20260701.dumps(
                    {
                        "ok": True,
                        "text": answer_text,
                        "assistant_message": {
                            "role": "assistant",
                            "content": answer_text,
                            "text": answer_text,
                            "attachments": [],
                        },
                        "route":
                            "project_brain_general_intelligence",
                        "route_taken":
                            "project_brain_general_intelligence",
                        "debug": {
                            "route":
                                "project_brain_general_intelligence",
                            "route_taken":
                                "project_brain_general_intelligence",
                            "intent":
                                answer_intent,
                            "compact_project_context_delegated":
                                True,
                        },
                        "meta": {
                            "route":
                                "project_brain_general_intelligence",
                            "strategy":
                                "project_brain_general_intelligence",
                        },
                    },
                    ensure_ascii=False,
                ),
                mimetype="application/json",
            )


        except Exception as exc:
            try:
                print(
                    "[NOVA_COMPACT_PROJECT_CONTEXT_DELEGATE_TO_PROJECT_BRAIN_20260701] bypass:",
                    exc,
                )
            except Exception:
                pass

            return None


    def _nova_compact_project_load_context_20260701():
        try:
            from nova_backend.services.project_brain_context_builder import (
                build_current_project_answer,
            )

            return str(
                build_current_project_answer()
                or ""
            ).strip()

        except Exception as exc:
            try:
                print(
                    "[NOVA_COMPACT_PROJECT_CONTEXT_FRESHNESS_BRIDGE_20260715] failed:",
                    exc,
                )
            except Exception:
                pass

            return ""


    def _nova_compact_project_payload_20260701(reply, data):

        session_id = ""
        if isinstance(data, dict):
            session_id = str(data.get("session_id") or data.get("active_session_id") or "").strip()

        return {
            "ok": True,
            "success": True,
            "content": reply,
            "message": reply,
            "response": reply,
            "session_id": session_id,
            "active_session_id": session_id,
            "assistant_message": {
                "role": "assistant",
                "content": reply,
                "attachments": [],
            },
            "route": "project_state_context",
            "route_taken": "project_state_context",
            "debug": {
                "route": "project_state_context",
                "route_taken": "project_state_context",
                "compact_project_context": True,
            },
            "meta": {
                "route": "project_state_context",
                "strategy": "compact_project_context",
            },
        }

    def _nova_compact_project_wrap_endpoint_20260701(app, endpoint_name):
        view = app.view_functions.get(endpoint_name)
        if not callable(view):
            return False

        if getattr(view, "_NOVA_API_CHAT_COMPACT_PROJECT_CONTEXT_20260701", False):
            return True

        def _nova_compact_project_wrapped_view_20260701(*args, **kwargs):
            try:
                data = _nova_compact_project_request_json_20260701()
                user_text = _nova_compact_project_request_text_20260701(data)

                if _nova_phase7b_is_local_unresolved_recall_20260711(
                    user_text
                ):
                    return view(
                        *args,
                        **kwargs,
                    )

                project_brain_response = _nova_compact_project_brain_response_20260701(user_text)
                if project_brain_response is not None:
                    return project_brain_response

                if _nova_compact_project_should_answer_20260701(user_text):
                    context = _nova_compact_project_load_context_20260701()

                    if context:
                        reply = (
                            "Current Nova project state:\n"
                            f"{context}\n\n"
                            f"Current blocker: {context.blocker}\n"
                            "This is the compact Project Brain state view for the current Nova work."
                        )

                        payload = _nova_compact_project_payload_20260701(reply, data)
                        encoded = _nova_compact_project_json_20260701.dumps(payload, ensure_ascii=False)
                        return _NovaCompactProjectResponse20260701(
                            encoded,
                            status=200,
                            mimetype="application/json",
                        )
            except Exception as _nova_compact_project_route_error_20260701:
                try:
                    print(
                        "[NOVA_API_CHAT_COMPACT_PROJECT_CONTEXT_20260701] bypass:",
                        _nova_compact_project_route_error_20260701,
                    )
                except Exception:
                    pass

            return view(*args, **kwargs)

        _nova_compact_project_wrapped_view_20260701.__name__ = getattr(
            view,
            "__name__",
            "_nova_compact_project_wrapped_view_20260701",
        )
        _nova_compact_project_wrapped_view_20260701._NOVA_API_CHAT_COMPACT_PROJECT_CONTEXT_20260701 = True

        app.view_functions[endpoint_name] = _nova_compact_project_wrapped_view_20260701
        return True

except Exception as _nova_compact_project_install_error_20260701:
    try:
        print(
            "[NOVA_API_CHAT_COMPACT_PROJECT_CONTEXT_20260701] failed:",
            _nova_compact_project_install_error_20260701,
        )
    except Exception:
        pass

# NOVA_API_CHAT_AUTONOMY_TASK_BRIEF_20260701
# Prefix-only autonomy task brief route.
# Safe mode: proposal-only. Does not edit files, run commands, or execute plans.
try:
    import json as _nova_autonomy_json_20260701
    import importlib.util as _nova_autonomy_importlib_util_20260701
    from pathlib import Path as _NovaAutonomyPath20260701
    from flask import request as _nova_autonomy_request_20260701
    from flask import Response as _NovaAutonomyResponse20260701

    _NOVA_AUTONOMY_PREFIXES_20260701 = (
        "autonomy:",
        "autonomy ",
        "task brain:",
        "safe task:",
        "safe autonomy:",
    )

    def _nova_autonomy_request_json_20260701():
        try:
            data = _nova_autonomy_request_20260701.get_json(silent=True) or {}
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _nova_autonomy_request_text_20260701(data):
        for key in ("message", "user_text", "text", "prompt"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _nova_autonomy_goal_from_text_20260701(user_text):
        text = str(user_text or "").strip()
        low = text.lower()

        for prefix in _NOVA_AUTONOMY_PREFIXES_20260701:
            if low.startswith(prefix):
                return text[len(prefix):].strip() or "Improve Nova safely."

        return ""

    def _nova_autonomy_load_formatter_20260701():
        service_path = (
            _NovaAutonomyPath20260701(__file__)
            .resolve()
            .parent
            / "autonomy_task_brain.py"
        )

        spec = _nova_autonomy_importlib_util_20260701.spec_from_file_location(
            "_nova_autonomy_task_brain_direct_20260701",
            str(service_path),
        )

        if not spec or not spec.loader:
            return None

        module = _nova_autonomy_importlib_util_20260701.module_from_spec(spec)
        spec.loader.exec_module(module)

        formatter = getattr(module, "format_autonomy_task_brief", None)
        return formatter if callable(formatter) else None

    def _nova_autonomy_payload_20260701(reply, data):
        session_id = ""
        if isinstance(data, dict):
            session_id = str(data.get("session_id") or data.get("active_session_id") or "").strip()

        return {
            "ok": True,
            "success": True,
            "content": reply,
            "message": reply,
            "response": reply,
            "session_id": session_id,
            "active_session_id": session_id,
            "assistant_message": {
                "role": "assistant",
                "content": reply,
                "attachments": [],
            },
            "route": "autonomy_task_brief",
            "route_taken": "autonomy_task_brief",
            "debug": {
                "route": "autonomy_task_brief",
                "route_taken": "autonomy_task_brief",
                "autonomy_mode": "proposal_only",
            },
            "meta": {
                "route": "autonomy_task_brief",
                "strategy": "proposal_only",
            },
        }

    def _nova_autonomy_wrap_endpoint_20260701(app, endpoint_name):
        view = app.view_functions.get(endpoint_name)
        if not callable(view):
            return False

        if getattr(view, "_NOVA_API_CHAT_AUTONOMY_TASK_BRIEF_20260701", False):
            return True

        def _nova_autonomy_wrapped_view_20260701(*args, **kwargs):
            try:
                data = _nova_autonomy_request_json_20260701()
                user_text = _nova_autonomy_request_text_20260701(data)
                goal = _nova_autonomy_goal_from_text_20260701(user_text)

                if goal:
                    formatter = _nova_autonomy_load_formatter_20260701()

                    if formatter:
                        reply = formatter(goal)
                        payload = _nova_autonomy_payload_20260701(reply, data)
                        encoded = _nova_autonomy_json_20260701.dumps(payload, ensure_ascii=False)
                        return _NovaAutonomyResponse20260701(
                            encoded,
                            status=200,
                            mimetype="application/json",
                        )
            except Exception as _nova_autonomy_route_error_20260701:
                try:
                    print(
                        "[NOVA_API_CHAT_AUTONOMY_TASK_BRIEF_20260701] bypass:",
                        _nova_autonomy_route_error_20260701,
                    )
                except Exception:
                    pass

            return view(*args, **kwargs)

        _nova_autonomy_wrapped_view_20260701.__name__ = getattr(
            view,
            "__name__",
            "_nova_autonomy_wrapped_view_20260701",
        )
        _nova_autonomy_wrapped_view_20260701._NOVA_API_CHAT_AUTONOMY_TASK_BRIEF_20260701 = True

        app.view_functions[endpoint_name] = _nova_autonomy_wrapped_view_20260701
        return True

except Exception as _nova_autonomy_install_error_20260701:
    try:
        print(
            "[NOVA_API_CHAT_AUTONOMY_TASK_BRIEF_20260701] failed:",
            _nova_autonomy_install_error_20260701,
        )
    except Exception:
        pass


def install_project_chat_response_router(app):
    try:
        wrapped = 0

        for endpoint_name, view in list(app.view_functions.items()):
            if _nova_api_project_state_wrap_endpoint_20260630(app, endpoint_name):
                wrapped += 1

            if _nova_natural_project_wrap_endpoint_20260701(app, endpoint_name):
                wrapped += 1

            if _nova_compact_project_wrap_endpoint_20260701(app, endpoint_name):
                wrapped += 1

            if _nova_autonomy_wrap_endpoint_20260701(app, endpoint_name):
                wrapped += 1

        print(
            "[NOVA_PROJECT_CHAT_RESPONSE_ROUTER_SERVICE] installed:",
            wrapped,
        )

    except Exception as error:
        print(
            "[NOVA_PROJECT_CHAT_RESPONSE_ROUTER_SERVICE] failed:",
            error,
        )

def normalize_text(value):
    text = str(value or "").strip()
    return " ".join(text.split())

def build_project_answer(user_text):
    mapped = _nova_natural_project_prompt_map_20260701(user_text)

    if not mapped:
        return None

    return _nova_natural_project_load_answer_20260701(mapped)


def apply_project_route(payload, reply):
    return _nova_natural_project_payload_20260701(
        reply,
        payload,
    )

def patch_payload(payload, reply):
    return apply_project_route(
        payload,
        reply,
    )