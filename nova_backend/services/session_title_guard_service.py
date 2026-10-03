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
            return service.set_auto_title_if_untitled(session_id, clean_title)

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

        # A request may have started before the user renamed this chat. Check
        # persisted metadata as well as the response snapshot so a late hook
        # cannot restore an automatic title over the user's choice.
        try:
            from nova_backend.services import session_service
            service = getattr(session_service, "session_service", None)
            persisted = service.get_session(session.get("id")) if service else None
            if session.get("title_manual") or (isinstance(persisted, dict) and persisted.get("title_manual")):
                if isinstance(persisted, dict):
                    session["title"] = str(persisted.get("title") or session.get("title") or "New Chat")
                return response
        except Exception:
            if session.get("title_manual"):
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
                "text_chars": len(str(user_text or "")),
                "route": route,
                "source": source,
            },
        )

        if cleaned != old_title:
            session["title"] = cleaned

            persisted = persist_title(
                session.get("id"),
                cleaned,
            )
            if isinstance(persisted, dict):
                session["title"] = str(persisted.get("title") or cleaned)

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
