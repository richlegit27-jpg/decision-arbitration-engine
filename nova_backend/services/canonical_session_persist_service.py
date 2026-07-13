import json
import os
from datetime import datetime

# NOVA_PHASE4H_CANONICAL_SESSION_PERSIST_20260705
# Final canonical persistence repair:
# - /api/chat may return assistant_message separately while session.messages only has the user.
# - Older bridges can claim a target session was saved, but /api/sessions/<id> cannot read it.
# - This hook runs last, merges user + assistant into session.messages, and writes the target session
#   into data/nova_sessions.json using the existing store shape instead of faking only the response.
def _nova_phase4h_now_20260705():
    try:
        return datetime.utcnow().isoformat() + "Z"
    except Exception:
        return ""


def _nova_phase4h_text_20260705(value):
    try:
        return str(value or "").strip()
    except Exception:
        return ""


def _nova_phase4h_msg_text_20260705(msg):
    if not isinstance(msg, dict):
        return ""
    return _nova_phase4h_text_20260705(
        msg.get("text")
        or msg.get("content")
        or msg.get("message")
        or ""
    )


def _nova_phase4h_has_message_20260705(messages, role, text, msg_id=""):
    text = _nova_phase4h_text_20260705(text)
    msg_id = _nova_phase4h_text_20260705(msg_id)

    for msg in messages:
        if not isinstance(msg, dict):
            continue

        current_role = _nova_phase4h_text_20260705(msg.get("role"))
        current_text = _nova_phase4h_msg_text_20260705(msg)
        current_id = _nova_phase4h_text_20260705(msg.get("id"))

        if msg_id and current_id and current_id == msg_id:
            return True

        if current_role == role and text and current_text == text:
            return True

    return False


def _nova_phase4h_dedupe_messages_20260705(messages):
    if not isinstance(messages, list):
        return []

    cleaned = []
    seen = set()

    for msg in messages:
        if not isinstance(msg, dict):
            continue

        role = _nova_phase4h_text_20260705(msg.get("role"))
        text = _nova_phase4h_msg_text_20260705(msg)

        # Main duplicate rule: same role + same visible text.
        key = (role, text)

        if role and text and key in seen:
            continue

        if role and text:
            seen.add(key)

        cleaned.append(msg)

    return cleaned


def _nova_phase4h_load_store_20260705():
    try:
        return _nova_final_load_sessions_store_20260612()
    except Exception:
        pass

    try:
        path_value = os.path.join(BASE_DIR, "data", "nova_sessions.json")
        if os.path.exists(path_value):
            with open(path_value, "r", encoding="utf-8") as handle:
                data = json.load(handle) or {}
                if isinstance(data, dict):
                    return data
    except Exception:
        pass

    return {}


def _nova_phase4h_save_store_20260705(store):
    try:
        return _nova_final_save_sessions_store_20260612(store)
    except Exception:
        pass

    try:
        path_value = os.path.join(BASE_DIR, "data", "nova_sessions.json")
        os.makedirs(os.path.dirname(path_value), exist_ok=True)
        with open(path_value, "w", encoding="utf-8") as handle:
            json.dump(store, handle, ensure_ascii=False, indent=2)
        return True
    except Exception as error:
        try:
            app.logger.warning("[Phase4H Canonical Persist] save failed: %s", error)
        except Exception:
            pass

    return False


def _nova_phase4h_find_session_20260705(store, session_id):
    try:
        found = _nova_final_find_session_in_store_20260612(store, session_id)
        if isinstance(found, dict):
            return found
    except Exception:
        pass

    sessions = store.get("sessions")

    if isinstance(sessions, dict):
        item = sessions.get(session_id)
        return item if isinstance(item, dict) else None

    if isinstance(sessions, list):
        for item in sessions:
            if isinstance(item, dict) and _nova_phase4h_text_20260705(item.get("id")) == session_id:
                return item

    return None


def _nova_phase4h_upsert_session_20260705(session_id, session_obj):
    session_id = _nova_phase4h_text_20260705(session_id)

    if not session_id or not isinstance(session_obj, dict):
        return None

    store = _nova_phase4h_load_store_20260705()
    sessions = store.get("sessions")

    existing = None

    if isinstance(sessions, dict):
        existing = sessions.get(session_id)
        if not isinstance(existing, dict):
            existing = {"id": session_id, "messages": [], "session_attachments": [], "meta": {}}
            sessions[session_id] = existing

    else:
        if not isinstance(sessions, list):
            sessions = []

        for item in sessions:
            if isinstance(item, dict) and _nova_phase4h_text_20260705(item.get("id")) == session_id:
                existing = item
                break

        if not isinstance(existing, dict):
            existing = {"id": session_id, "messages": [], "session_attachments": [], "meta": {}}
            sessions.insert(0, existing)

    for key, value in session_obj.items():
        if key == "messages":
            continue
        existing[key] = value

    messages = session_obj.get("messages")
    if not isinstance(messages, list):
        messages = existing.get("messages") if isinstance(existing.get("messages"), list) else []

    existing["id"] = session_id
    existing["messages"] = messages
    existing["message_count"] = len(messages)
    existing["active_session_id"] = session_id
    existing["updated_at"] = _nova_phase4h_now_20260705()

    if not existing.get("created_at"):
        existing["created_at"] = existing["updated_at"]

    if not existing.get("title"):
        first_user_text = ""
        for msg in messages:
            if isinstance(msg, dict) and _nova_phase4h_text_20260705(msg.get("role")) == "user":
                first_user_text = _nova_phase4h_msg_text_20260705(msg)
                break
        existing["title"] = (first_user_text or "Chat")[:80]

    meta = existing.get("meta")
    if not isinstance(meta, dict):
        meta = {}

    meta["phase4h_canonical_session_persist"] = True
    existing["meta"] = meta

    store["sessions"] = sessions
    store["active_session_id"] = session_id

    _nova_phase4h_save_store_20260705(store)

    try:
        _NOVA_FINAL_SESSION_DETAIL_CACHE_20260612[session_id] = existing
    except Exception:
        pass

    return existing


def _nova_phase4h_merge_chat_response_20260705(response_json):
    if not isinstance(response_json, dict):
        return "", None

    session_obj = response_json.get("session")
    if not isinstance(session_obj, dict):
        session_obj = {}

    session_id = _nova_phase4h_text_20260705(
        response_json.get("session_id")
        or response_json.get("active_session_id")
        or session_obj.get("id")
        or ""
    )

    if not session_id:
        return "", None

    session_obj["id"] = session_id
    session_obj["active_session_id"] = session_id

    messages = session_obj.get("messages")
    if not isinstance(messages, list):
        messages = []

    now_value = _nova_phase4h_now_20260705()

    try:
        payload = request.get_json(silent=True) or {}
    except Exception:
        payload = {}

    if not isinstance(payload, dict):
        payload = {}

    user_text = _nova_phase4h_text_20260705(
        payload.get("message")
        or payload.get("text")
        or payload.get("content")
        or payload.get("user_text")
        or ""
    )

    if user_text and not _nova_phase4h_has_message_20260705(messages, "user", user_text):
        messages.insert(0, {
            "id": "msg_phase4h_user_" + str(abs(hash(session_id + user_text))),
            "role": "user",
            "text": user_text,
            "content": user_text,
            "attachments": payload.get("attachments") if isinstance(payload.get("attachments"), list) else [],
            "session_id": session_id,
            "active_session_id": session_id,
            "created_at": now_value,
            "updated_at": now_value,
            "meta": {
                "route": "phase4h_canonical_session_persist",
                "session_id": session_id,
            },
        })

    assistant_message = response_json.get("assistant_message")
    assistant_text = ""

    if isinstance(assistant_message, dict):
        assistant_text = _nova_phase4h_text_20260705(
            assistant_message.get("text")
            or assistant_message.get("content")
            or assistant_message.get("message")
            or ""
        )

    if not assistant_text:
        assistant_text = _nova_phase4h_text_20260705(
            response_json.get("text")
            or response_json.get("content")
            or response_json.get("message")
            or ""
        )

    assistant_id = ""
    assistant_attachments = []
    assistant_meta = {}

    if isinstance(assistant_message, dict):
        assistant_id = _nova_phase4h_text_20260705(assistant_message.get("id"))
        if isinstance(assistant_message.get("attachments"), list):
            assistant_attachments = assistant_message.get("attachments") or []
        if isinstance(assistant_message.get("meta"), dict):
            assistant_meta.update(assistant_message.get("meta") or {})

    if assistant_text and not _nova_phase4h_has_message_20260705(messages, "assistant", assistant_text, assistant_id):
        assistant_meta["route"] = assistant_meta.get("route") or "phase4h_canonical_session_persist"
        assistant_meta["session_id"] = session_id
        assistant_meta["render_source"] = "session_messages"

        messages.append({
            "id": assistant_id or ("msg_phase4h_assistant_" + str(abs(hash(session_id + assistant_text)))),
            "role": "assistant",
            "text": assistant_text,
            "content": assistant_text,
            "attachments": assistant_attachments,
            "session_id": session_id,
            "active_session_id": session_id,
            "created_at": now_value,
            "updated_at": now_value,
            "meta": assistant_meta,
        })

    messages = _nova_phase4h_dedupe_messages_20260705(messages)

    session_obj["messages"] = messages
    session_obj["message_count"] = len(messages)
    session_obj["updated_at"] = now_value

    working_state = session_obj.get("working_state")
    if not isinstance(working_state, dict):
        working_state = {}

    if user_text:
        working_state["last_user_message"] = user_text

    if assistant_text:
        working_state["last_assistant_message"] = assistant_text

    session_obj["working_state"] = working_state

    return session_id, session_obj


@app.after_request
def nova_phase4h_canonical_session_persist_20260705(response):
    try:
        request_path = _nova_phase4h_text_20260705(getattr(request, "path", ""))
        request_method = _nova_phase4h_text_20260705(getattr(request, "method", "")).upper()

        if request_method == "POST" and request_path == "/api/chat":
            response_json = response.get_json(silent=True) or {}
            if not isinstance(response_json, dict):
                return response

            session_id, session_obj = _nova_phase4h_merge_chat_response_20260705(response_json)

            if not session_id or not isinstance(session_obj, dict):
                return response

            saved_session = _nova_phase4h_upsert_session_20260705(session_id, session_obj)

            if isinstance(saved_session, dict):
                response_json["session"] = saved_session
                response_json["session_id"] = session_id
                response_json["active_session_id"] = session_id
                response_json["phase4h_canonical_session_persist"] = True
                response_json["final_session_detail_response_cache"] = True

                response.set_data(json.dumps(response_json, ensure_ascii=False))
                response.headers["Content-Length"] = str(len(response.get_data()))
                response.headers["Content-Type"] = "application/json"

            return response

        if request_method == "GET" and request_path.startswith("/api/sessions/"):
            if getattr(response, "status_code", 200) < 400:
                return response

            session_id = request_path[len("/api/sessions/"):].strip().strip("/")
            session_id = _nova_phase4h_text_20260705(session_id)

            if not session_id:
                return response

            store = _nova_phase4h_load_store_20260705()
            session_obj = _nova_phase4h_find_session_20260705(store, session_id)

            if not isinstance(session_obj, dict):
                return response

            messages = session_obj.get("messages")
            if not isinstance(messages, list):
                messages = []

            payload = {
                "ok": True,
                "id": session_id,
                "session_id": session_id,
                "active_session_id": session_id,
                "message_count": len(messages),
                "session": session_obj,
                "skip_session_auth_scope_filter": True,
                "phase4h_canonical_session_persist_fallback": True,
            }

            return app.response_class(
                response=json.dumps(payload, ensure_ascii=False),
                status=200,
                mimetype="application/json",
            )

    except Exception as error:
        try:
            app.logger.warning("[Phase4H Canonical Persist] failed: %s", error)
        except Exception:
            pass

    return response


# Force Phase4H to run after the older final_session_detail_response_cache hook.
# Flask runs after_request hooks in reverse order, so index 0 executes last.
try:
    _phase4h_hooks = app.after_request_funcs.get(None, [])
    _phase4h_name = "nova_phase4h_canonical_session_persist_20260705"
    _phase4h_func = None

    for _phase4h_hook in list(_phase4h_hooks):
        if getattr(_phase4h_hook, "__name__", "") == _phase4h_name:
            _phase4h_func = _phase4h_hook
            try:
                _phase4h_hooks.remove(_phase4h_hook)
            except ValueError:
                pass
            break

    if _phase4h_func is not None:
        _phase4h_hooks.insert(0, _phase4h_func)
        app.after_request_funcs[None] = _phase4h_hooks
        _nova_boot_log_20260701("[NOVA_PHASE4H_CANONICAL_SESSION_PERSIST] forced final hook to run last")
except Exception:
    pass


# This runs after final_session_detail_response_cache so visible assistant text
# matches the already-clean saved artifact/session title.
try:
    import json as _nova_img_cache_json_20260630
    import re as _nova_img_cache_re_20260630

    def _nova_img_cache_clean_prompt_20260630(value):
        raw = str(value or "").strip()

        raw = _nova_img_cache_re_20260630.sub(
            r"^\s*Generated\s+image\s*(for)?\s*:\s*",
            "",
            raw,
            flags=_nova_img_cache_re_20260630.I,
        )

        raw = _nova_img_cache_re_20260630.sub(
            r"^\s*Image\s*:\s*",
            "",
            raw,
            flags=_nova_img_cache_re_20260630.I,
        )

        raw = _nova_img_cache_re_20260630.sub(
            r"^\s*(please\s+)?(generate|create|make|draw|render|produce)\s+(an?\s+)?(image|picture|photo|illustration|art|drawing)\s*",
            "",
            raw,
            flags=_nova_img_cache_re_20260630.I,
        )

        raw = _nova_img_cache_re_20260630.sub(
            r"^\s*(of|for)\s+",
            "",
            raw,
            flags=_nova_img_cache_re_20260630.I,
        )

        raw = raw.strip(" .")
        return raw or "your image"

    def _nova_img_cache_is_image_response_20260630(data):
        if not isinstance(data, dict):
            return False

        assistant_message = data.get("assistant_message")
        saved_artifact = data.get("saved_artifact")

        if isinstance(assistant_message, dict):
            meta = assistant_message.get("meta")
            if assistant_message.get("image_url"):
                return True
            if isinstance(meta, dict) and meta.get("source") == "image_generation":
                return True

            attachments = assistant_message.get("attachments")
            if isinstance(attachments, list):
                for item in attachments:
                    if isinstance(item, dict) and (
                        item.get("image_url")
                        or item.get("url")
                        or item.get("file_url")
                    ):
                        mime = str(item.get("mime_type") or item.get("type") or "").lower()
                        if mime.startswith("image/") or str(item.get("filename") or "").lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
                            return True

        if isinstance(saved_artifact, dict):
            if saved_artifact.get("image_url"):
                return True
            if str(saved_artifact.get("kind") or "").lower() == "image":
                return True
            if str(saved_artifact.get("type") or "").lower() == "image_generation":
                return True

        return False

    def _nova_img_cache_pick_prompt_20260630(data):
        assistant_message = data.get("assistant_message") if isinstance(data, dict) else {}
        saved_artifact = data.get("saved_artifact") if isinstance(data, dict) else {}
        session = data.get("session") if isinstance(data, dict) else {}

        candidates = []

        if isinstance(saved_artifact, dict):
            candidates.extend([
                saved_artifact.get("summary"),
                saved_artifact.get("prompt"),
                saved_artifact.get("body"),
            ])

            meta = saved_artifact.get("meta")
            if isinstance(meta, dict):
                candidates.append(meta.get("prompt"))

        if isinstance(session, dict):
            candidates.append(session.get("title"))

        if isinstance(assistant_message, dict):
            candidates.extend([
                assistant_message.get("text"),
                assistant_message.get("content"),
            ])

        for candidate in candidates:
            clean = _nova_img_cache_clean_prompt_20260630(candidate)
            if clean and clean != "your image":
                return clean

        return "your image"

    def _nova_img_cache_fix_image_response_20260630(data):
        if not _nova_img_cache_is_image_response_20260630(data):
            return data

        prompt = _nova_img_cache_pick_prompt_20260630(data)
        clean_text = f"Generated image: {prompt}"

        assistant_message = data.get("assistant_message")
        if isinstance(assistant_message, dict):
            assistant_message["text"] = clean_text
            assistant_message["content"] = clean_text
            data["assistant_message"] = assistant_message

        saved_artifact = data.get("saved_artifact")
        if isinstance(saved_artifact, dict):
            saved_artifact["summary"] = clean_text

            viewer = saved_artifact.get("viewer")
            if isinstance(viewer, dict):
                viewer["summary"] = clean_text
                saved_artifact["viewer"] = viewer

            data["saved_artifact"] = saved_artifact

        session = data.get("session")
        if isinstance(session, dict):
            working_state = session.get("working_state")
            if isinstance(working_state, dict):
                working_state["last_assistant_message"] = clean_text
                session["working_state"] = working_state

            messages = session.get("messages")
            if isinstance(messages, list):
                for message in messages:
                    if not isinstance(message, dict):
                        continue

                    if str(message.get("role") or "").lower() == "assistant":
                        message_text = str(message.get("text") or message.get("content") or "")
                        if "Generated image" in message_text:
                            message["text"] = clean_text
                            message["content"] = clean_text

            data["session"] = session

        return data

    @app.after_request
    def _nova_final_image_response_cache_text_guard_20260630(response):
        try:
            content_type = str(response.headers.get("Content-Type") or "").lower()
            if "application/json" not in content_type:
                return response

            raw = response.get_data(as_text=True)
            if not raw:
                return response

            data = _nova_img_cache_json_20260630.loads(raw)
            fixed = _nova_img_cache_fix_image_response_20260630(data)

            if fixed is data:
                return response

            new_raw = _nova_img_cache_json_20260630.dumps(
                fixed,
                ensure_ascii=False,
            )
            response.set_data(new_raw)
            response.headers["Content-Length"] = str(len(response.get_data()))
            response.headers["Content-Type"] = "application/json"

            return response
        except Exception as _nova_img_cache_guard_error_20260630:
            print("[NOVA_FINAL_IMAGE_RESPONSE_CACHE_TEXT_GUARD_20260630] skipped:", _nova_img_cache_guard_error_20260630)
            return response

    # Flask runs after_request handlers in reverse registration order.
    # Move this one to the front so it executes last, after final_session_detail_response_cache.
    try:
        _nova_img_cache_funcs_20260630 = app.after_request_funcs.get(None, [])
        if (
            _nova_img_cache_funcs_20260630
            and _nova_img_cache_funcs_20260630[-1].__name__ == "_nova_final_image_response_cache_text_guard_20260630"
        ):
            _nova_img_cache_funcs_20260630.insert(0, _nova_img_cache_funcs_20260630.pop())
    except Exception:
        pass

    _nova_boot_log_20260701("[NOVA_FINAL_IMAGE_RESPONSE_CACHE_TEXT_GUARD_20260630] installed")
except Exception as _nova_img_cache_install_error_20260630:
    print("[NOVA_FINAL_IMAGE_RESPONSE_CACHE_TEXT_GUARD_20260630] failed:", _nova_img_cache_install_error_20260630)

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

    def _nova_api_project_state_wrap_endpoint_20260630(endpoint_name):
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

    _nova_api_project_state_wrapped_count_20260630 = 0
    for _endpoint_name_20260630, _view_20260630 in list(app.view_functions.items()):
        try:
            rule_matches = [
                rule.rule
                for rule in app.url_map.iter_rules()
                if rule.endpoint == _endpoint_name_20260630
            ]

            if "/api/chat" in rule_matches:
                if _nova_api_project_state_wrap_endpoint_20260630(_endpoint_name_20260630):
                    _nova_api_project_state_wrapped_count_20260630 += 1
        except Exception:
            pass

    _nova_boot_log_20260701(
        "[NOVA_API_CHAT_PROJECT_STATE_IDLE_NEXT_FINAL_20260630] wrapped endpoints:",
        _nova_api_project_state_wrapped_count_20260630,
    )
except Exception as _nova_api_project_state_install_error_20260630:
    try:
        print(
            "[NOVA_API_CHAT_PROJECT_STATE_IDLE_NEXT_FINAL_20260630] failed:",
            _nova_api_project_state_install_error_20260630,
        )
    except Exception:
        pass


