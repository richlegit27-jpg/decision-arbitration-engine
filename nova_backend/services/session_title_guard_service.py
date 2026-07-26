import json


def persist_title(session_id, clean_title):
    try:
        if not session_id:
            return

        from nova_backend.services import session_service

        service = getattr(
            session_service,
            "session_service",
            None,
        )

        if service:
            session = service.get_session(session_id) or {}

            if isinstance(session, dict):
                session["title"] = clean_title
                service.save(
                    service.get_all(),
                    active=session_id,
                )

    except Exception as error:
        print(
            "[SESSION_TITLE_GUARD] persist skipped:",
            error,
        )


def apply_response_title_guard(response):
    try:
        request = getattr(
            response,
            "_nova_request",
            None,
        )

        if request is None:
            return response

        request_path = str(
            getattr(request, "path", "")
            or ""
        )

        request_method = str(
            getattr(request, "method", "")
            or ""
        ).upper()

        if request_method != "POST" or request_path != "/api/chat":
            return response

        data = response.get_json(silent=True) or {}

        if not isinstance(data, dict):
            return response

        user_text = str(
            data.get("user_text")
            or data.get("text")
            or data.get("message")
            or ""
        ).strip()

        session = data.get("session")

        if not isinstance(session, dict):
            return response

        old_title = str(
            session.get("title")
            or ""
        ).strip()

        route = str(
            data.get("route")
            or ""
        ).strip()

        source = str(
            data.get("source")
            or ""
        ).strip()

        cleaned = clean_title(
            old_title,
            user_text,
            route,
            source,
        )

        print(
            "[TITLE GUARD DEBUG]",
            {
                "old_title": old_title,
                "user_text": user_text,
                "route": route,
                "source": source,
                "cleaned": cleaned,
            },
        )

        if cleaned != old_title:
            session["title"] = cleaned

            persist_title(
                session.get("id"),
                cleaned,
            )

            response.set_data(
                json.dumps(
                    data,
                    ensure_ascii=False,
                )
            )

        return response

    except Exception as error:
        print(
            "[SESSION_TITLE_GUARD] skipped:",
            error,
        )

    return response


def is_garbage_title(value) -> bool:
    text = str(value or "")
    compact = "".join(text.split())

    if not compact:
        return False

    lower = compact.lower()

    return lower in {
        "webfetch",
        "web fetch",
        "sourcepreview",
        "source preview",
        "generatedimage",
        "generated image",
    }


def clean_title(title, user_text, route, source):
    current = str(title or "").strip()

    if (
        str(route or "").lower() == "accidental_input_guard"
        or str(source or "").lower() == "accidental_input_guard"
        or is_garbage_title(current)
        or is_garbage_title(user_text)
    ):
        return "New Chat"

    if current.lower() in {
        "",
        "web fetch",
        "source preview",
        "generated image",
    }:
        candidate = str(
            user_text or ""
        ).replace(
            "\n",
            " ",
        ).strip()

        if (
            candidate
            and not is_garbage_title(candidate)
            and len(candidate) >= 4
        ):
            return candidate[:60]

        return "New Chat"

    return current or "New Chat"


def install(app):
    @app.after_request
    def nova_final_title_guard_20260630(response):
        try:
            return apply_response_title_guard(response)

        except Exception as error:
            print(
                "[NOVA_FINAL_TITLE_GUARD_20260630] skipped:",
                error,
            )

        return response