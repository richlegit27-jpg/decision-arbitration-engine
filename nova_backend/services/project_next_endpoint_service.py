from flask import jsonify


def build_project_next_response(
    answer,
    session_id="",
    route="project_next",
):
    return jsonify(
        {
            "ok": True,
            "assistant_message": {
                "role": "assistant",
                "text": str(answer or "").strip(),
            },
            "active_session_id": str(session_id or "").strip(),
            "route": route,
        }
    )


def install_project_next_endpoint_wrapper(app):

    def clean_text(value):
        return " ".join(
            str(value or "")
            .lower()
            .strip()
            .split()
        )

    def is_project_next_request(text):

        clean = clean_text(text)

        prefixes = (
            "build",
            "create",
            "fix",
            "debug",
            "implement",
            "plan",
            "make",
            "upgrade",
        )

        return clean.startswith(prefixes)

    @app.before_request
    def project_next_endpoint_wrapper():

        try:
            from flask import request

            if request.path != "/api/chat":
                return None

            if request.method != "POST":
                return None

            data = request.get_json(
                silent=True
            ) or {}

            user_text = str(
                data.get("message")
                or data.get("user_text")
                or data.get("text")
                or ""
            ).strip()

            if not user_text:
                return None

            if not is_project_next_request(
                user_text
            ):
                return None

            from nova_backend.services.project_chat_response_router_service import (
                route_project_chat_response,
            )

            result = route_project_chat_response(
                user_text
            )

            if not result:
                return None

            session_id = str(
                data.get("session_id")
                or data.get("active_session_id")
                or ""
            )

            return build_project_next_response(
                result,
                session_id=session_id,
                route="project_next_endpoint_service",
            )

        except Exception as exc:
            print(
                "[NOVA_PROJECT_NEXT_ENDPOINT_SERVICE] failed:",
                exc,
            )

        return None

    print(
        "[NOVA_PROJECT_NEXT_ENDPOINT_SERVICE] installed"
    )