import json
import importlib.util
from pathlib import Path
from flask import request


class ProjectStateRouteGuardService:

    def load_answer(self, user_text):
        service_path = (
            Path(__file__)
            .resolve()
            .parent
            / "project_state_service.py"
        )

        spec = importlib.util.spec_from_file_location(
            "_nova_project_state_service",
            str(service_path),
        )

        if not spec or not spec.loader:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        answer_fn = getattr(
            module,
            "answer_project_state_question",
            None,
        )

        if not callable(answer_fn):
            return None

        return answer_fn(
            user_text,
            runtime_execution_state=None,
        )

    def patch_payload(self, payload, reply):
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

    def content(self, payload):
        if not isinstance(payload, dict):
            return ""

        assistant = payload.get("assistant_message")

        if isinstance(assistant, dict):
            value = assistant.get("content")

            if isinstance(value, str):
                return value

        for key in (
            "content",
            "response",
            "message",
            "text",
            "answer",
        ):
            value = payload.get(key)

            if isinstance(value, str):
                return value

        return ""

    def request_text(self):
        try:
            data = request.get_json(silent=True) or {}

            if isinstance(data, dict):
                for key in (
                    "message",
                    "user_text",
                    "text",
                    "prompt",
                ):
                    value = data.get(key)

                    if isinstance(value, str) and value.strip():
                        return value.strip()

        except Exception:
            pass

        return ""

    def install(self, app):
        try:

            def wrap_endpoint(app, endpoint_name):
                view = app.view_functions.get(endpoint_name)

                if not callable(view):
                    return False

                if getattr(
                    view,
                    "_NOVA_API_CHAT_PROJECT_STATE_IDLE_NEXT_FINAL_20260630",
                    False,
                ):
                    return True

                def wrapped_view(*args, **kwargs):
                    result = view(*args, **kwargs)

                    try:
                        user_text = self.request_text().lower()

                        if user_text not in {
                            "next",
                            "k",
                            "ok",
                            "okay",
                            "continue",
                        }:
                            return result

                        if not hasattr(result, "get_data"):
                            return result

                        if not hasattr(result, "set_data"):
                            return result

                        raw = result.get_data(as_text=True)
                        payload = json.loads(raw)

                        current_content = self.content(payload)

                        if (
                            "no active execution mission"
                            not in str(current_content or "").lower()
                        ):
                            return result

                        reply = self.load_answer(user_text)

                        if not reply:
                            return result

                        payload = self.patch_payload(
                            payload,
                            reply,
                        )

                        result.set_data(
                            json.dumps(
                                payload,
                                ensure_ascii=False,
                            )
                        )

                        try:
                            result.headers["Content-Length"] = str(
                                len(result.get_data())
                            )
                            result.headers["Content-Type"] = (
                                "application/json"
                            )

                        except Exception:
                            pass

                        return result

                    except Exception:
                        return result

                wrapped_view.__name__ = getattr(
                    view,
                    "__name__",
                    "wrapped_view",
                )

                wrapped_view._NOVA_API_CHAT_PROJECT_STATE_IDLE_NEXT_FINAL_20260630 = True

                app.view_functions[endpoint_name] = wrapped_view

                return True

            wrapped_count = 0

            for endpoint_name, view in list(
                app.view_functions.items()
            ):
                try:
                    rule_matches = [
                        rule.rule
                        for rule in app.url_map.iter_rules()
                        if rule.endpoint == endpoint_name
                    ]

                    if "/api/chat" in rule_matches:

                        if wrap_endpoint(
                            app,
                            endpoint_name,
                        ):
                            wrapped_count += 1

                except Exception:
                    pass

            try:
                print(
                    "[NOVA_API_CHAT_PROJECT_STATE_IDLE_NEXT_FINAL_20260630] wrapped endpoints:",
                    wrapped_count,
                )

            except Exception:
                pass

        except Exception as error:
            try:
                print(
                    "[NOVA_API_CHAT_PROJECT_STATE_IDLE_NEXT_FINAL_20260630] failed:",
                    error,
                )

            except Exception:
                pass