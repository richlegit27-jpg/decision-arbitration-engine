









# NOVA_CHAT_SERVICE_ATTACHMENT_WEB_SUPPRESSION_COMPAT_20260705
def _nova_attachment_guard_payload_from_call(*args, **kwargs):
    payload = {}

    for value in args:
        if isinstance(value, dict):
            payload.update(value)

    for key, value in kwargs.items():
        if isinstance(value, dict):
            payload[key] = value
            payload.update(value)
        else:
            payload[key] = value

    try:
        from flask import g, has_request_context, request

        if has_request_context():
            request_payload = request.get_json(silent=True) or {}

            if isinstance(request_payload, dict):
                payload.update(request_payload)

            boundary_attachments = getattr(g, "nova_api_chat_attachments", None) or []

            if boundary_attachments and not any(
                payload.get(key)
                for key in (
                    "attachments",
                    "files",
                    "uploads",
                    "uploaded_files",
                    "pending_attachments",
                )
            ):
                payload["attachments"] = list(boundary_attachments)
    except Exception:
        pass

    return payload


def _nova_attachment_guard_message_from_call(*args, **kwargs):
    for key in (
        "message",
        "text",
        "user_text",
        "prompt",
        "query",
        "user_message",
        "content",
    ):
        value = kwargs.get(key)

        if isinstance(value, str) and value.strip():
            return value

    for value in args:
        if isinstance(value, str) and value.strip():
            return value

        if isinstance(value, dict):
            for key in (
                "message",
                "text",
                "user_text",
                "prompt",
                "query",
                "user_message",
                "content",
            ):
                nested = value.get(key)

                if isinstance(nested, str) and nested.strip():
                    return nested

    payload = _nova_attachment_guard_payload_from_call(*args, **kwargs)

    for key in (
        "message",
        "text",
        "user_text",
        "prompt",
        "query",
        "user_message",
        "content",
    ):
        value = payload.get(key)

        if isinstance(value, str) and value.strip():
            return value

    return ""


def _nova_attachment_guard_has_explicit_web_request(text):
    import re

    return bool(
        re.search(
            r"\b(web|internet|search|look up|lookup|google|news|latest|current|today|online)\b",
            str(text or "").lower(),
        )
    )


def _nova_attachment_guard_should_suppress_current_web_call(*args, **kwargs):
    try:
        from nova_backend.services.chat_attachment_payload_normalizer import (
            normalize_api_chat_attachments,
        )
        from nova_backend.services.chat_attachment_intent_guard import (
            is_attachment_focused_message,
        )

        payload = _nova_attachment_guard_payload_from_call(*args, **kwargs)
        message = _nova_attachment_guard_message_from_call(*args, **kwargs)

        attachments = normalize_api_chat_attachments(payload)

        if not attachments:
            return False

        focused_payload = dict(payload)
        focused_payload["attachments"] = attachments

        attachment_focused = is_attachment_focused_message(message, focused_payload)
        explicit_web = _nova_attachment_guard_has_explicit_web_request(message)

        return bool(attachment_focused and not explicit_web)
    except Exception:
        return False


def _nova_attachment_guard_suppressed_web_result():
    return {
        "ok": True,
        "suppressed": True,
        "would_suppress_web": True,
        "reason": "attachment_focused_turn",
        "results": [],
        "items": [],
        "answer": "",
        "text": "",
    }


def _nova_attachment_guard_wrap_bool_route(name):
    original = globals().get(name)

    if not callable(original):
        return False

    if getattr(original, "_nova_attachment_guard_wrapped", False):
        return True

    def wrapped(*args, **kwargs):
        if _nova_attachment_guard_should_suppress_current_web_call(*args, **kwargs):
            return False

        return original(*args, **kwargs)

    wrapped._nova_attachment_guard_wrapped = True
    wrapped._nova_attachment_guard_original = original

    globals()[name] = wrapped

    return True


def _nova_attachment_guard_wrap_result_route(name):
    original = globals().get(name)

    if not callable(original):
        return False

    if getattr(original, "_nova_attachment_guard_wrapped", False):
        return True

    def wrapped(*args, **kwargs):
        if _nova_attachment_guard_should_suppress_current_web_call(*args, **kwargs):
            return _nova_attachment_guard_suppressed_web_result()

        return original(*args, **kwargs)

    wrapped._nova_attachment_guard_wrapped = True
    wrapped._nova_attachment_guard_original = original

    globals()[name] = wrapped

    return True





def _nova_attachment_guard_expand_call(*call_args, **call_kwargs):
    positional = list(call_args)
    keyword = dict(call_kwargs or {})

    # Regression tests call these helpers as:
    #   helper(args=(...), kwargs={...})
    # so unwrap that shape back into normal call arguments.
    if "args" in keyword:
        packed_args = keyword.pop("args")

        if isinstance(packed_args, (list, tuple)):
            positional.extend(list(packed_args))
        else:
            positional.append(packed_args)

    if "kwargs" in keyword:
        packed_kwargs = keyword.pop("kwargs")

        if isinstance(packed_kwargs, dict):
            keyword.update(packed_kwargs)

    return tuple(positional), keyword


def _nova_attachment_guard_payload_from_call(*args, **kwargs):
    args, kwargs = _nova_attachment_guard_expand_call(*args, **kwargs)
    payload = {}

    for value in args:
        if isinstance(value, dict):
            payload.update(value)

    for key, value in kwargs.items():
        if isinstance(value, dict):
            payload[key] = value
            payload.update(value)
        else:
            payload[key] = value

    try:
        from flask import g, has_request_context, request

        if has_request_context():
            request_payload = request.get_json(silent=True) or {}

            if isinstance(request_payload, dict):
                payload.update(request_payload)

            boundary_attachments = getattr(g, "nova_api_chat_attachments", None) or []

            if boundary_attachments and not any(
                payload.get(key)
                for key in (
                    "attachments",
                    "files",
                    "uploads",
                    "uploaded_files",
                    "pending_attachments",
                )
            ):
                payload["attachments"] = list(boundary_attachments)
    except Exception:
        pass

    return payload


def _nova_attachment_guard_message_from_call(*args, **kwargs):
    args, kwargs = _nova_attachment_guard_expand_call(*args, **kwargs)

    for key in (
        "message",
        "text",
        "user_text",
        "prompt",
        "query",
        "user_message",
        "content",
    ):
        value = kwargs.get(key)

        if isinstance(value, str) and value.strip():
            return value

    for value in args:
        if isinstance(value, str) and value.strip():
            return value

        if isinstance(value, dict):
            for key in (
                "message",
                "text",
                "user_text",
                "prompt",
                "query",
                "user_message",
                "content",
            ):
                nested = value.get(key)

                if isinstance(nested, str) and nested.strip():
                    return nested

    payload = _nova_attachment_guard_payload_from_call(*args, **kwargs)

    for key in (
        "message",
        "text",
        "user_text",
        "prompt",
        "query",
        "user_message",
        "content",
    ):
        value = payload.get(key)

        if isinstance(value, str) and value.strip():
            return value

    return ""


def _nova_attachment_guard_has_explicit_web_request(text):
    import re

    return bool(
        re.search(
            r"\b(web|internet|search|look up|lookup|google|news|latest|current|today|online)\b",
            str(text or "").lower(),
        )
    )


def _nova_attachment_guard_should_suppress_current_web_call(*args, **kwargs):
    try:
        from nova_backend.services.chat_attachment_payload_normalizer import (
            normalize_api_chat_attachments,
        )
        from nova_backend.services.chat_attachment_intent_guard import (
            is_attachment_focused_message,
        )

        args, kwargs = _nova_attachment_guard_expand_call(*args, **kwargs)
        payload = _nova_attachment_guard_payload_from_call(*args, **kwargs)
        message = _nova_attachment_guard_message_from_call(*args, **kwargs)

        attachments = normalize_api_chat_attachments(payload)

        if not attachments:
            return False

        focused_payload = dict(payload)
        focused_payload["attachments"] = attachments

        attachment_focused = is_attachment_focused_message(message, focused_payload)
        explicit_web = _nova_attachment_guard_has_explicit_web_request(message)

        return bool(attachment_focused and not explicit_web)
    except Exception:
        return False


def _nova_attachment_guard_suppressed_web_result():
    return {
        "ok": True,
        "available": True,
        "suppressed": True,
        "would_suppress_web": True,
        "reason": "attachment_focused_turn",
        "results": [],
        "items": [],
        "sources": [],
        "answer": "",
        "text": "",
    }


def _nova_attachment_guard_wrap_module_bool_route(name):
    original = globals().get(name)

    if not callable(original):
        return False

    if getattr(original, "_nova_attachment_guard_wrapped_v2", False):
        return True

    def wrapped(*args, **kwargs):
        if _nova_attachment_guard_should_suppress_current_web_call(*args, **kwargs):
            return False

        return original(*args, **kwargs)

    wrapped._nova_attachment_guard_wrapped_v2 = True
    wrapped._nova_attachment_guard_original = original

    globals()[name] = wrapped

    return True


def _nova_attachment_guard_wrap_module_result_route(name):
    original = globals().get(name)

    if not callable(original):
        return False

    if getattr(original, "_nova_attachment_guard_wrapped_v2", False):
        return True

    def wrapped(*args, **kwargs):
        if _nova_attachment_guard_should_suppress_current_web_call(*args, **kwargs):
            return _nova_attachment_guard_suppressed_web_result()

        return original(*args, **kwargs)

    wrapped._nova_attachment_guard_wrapped_v2 = True
    wrapped._nova_attachment_guard_original = original

    globals()[name] = wrapped

    return True


def _nova_attachment_guard_wrap_class_bool_route(cls, name):
    original = getattr(cls, name, None)

    if not callable(original):
        return False

    if getattr(original, "_nova_attachment_guard_wrapped_v2", False):
        return True

    def wrapped(self, *args, **kwargs):
        if _nova_attachment_guard_should_suppress_current_web_call(*args, **kwargs):
            return False

        return original(self, *args, **kwargs)

    wrapped._nova_attachment_guard_wrapped_v2 = True
    wrapped._nova_attachment_guard_original = original

    setattr(cls, name, wrapped)

    return True


def _nova_attachment_guard_wrap_class_result_route(cls, name):
    original = getattr(cls, name, None)

    if not callable(original):
        return False

    if getattr(original, "_nova_attachment_guard_wrapped_v2", False):
        return True

    def wrapped(self, *args, **kwargs):
        if _nova_attachment_guard_should_suppress_current_web_call(*args, **kwargs):
            return _nova_attachment_guard_suppressed_web_result()

        return original(self, *args, **kwargs)

    wrapped._nova_attachment_guard_wrapped_v2 = True
    wrapped._nova_attachment_guard_original = original

    setattr(cls, name, wrapped)

    return True


def _nova_attachment_guard_install_web_routing_suppression():
    wrapped_bool_methods = []
    wrapped_result_methods = []

    bool_route_names = (
        "_should_use_web",
        "_should_use_web_search",
        "_should_search_web",
        "_needs_web",
        "_needs_web_search",
        "_route_to_web",
        "_should_route_to_web",
        "should_use_web",
        "should_search_web",
        "needs_web_search",
    )

    result_route_names = (
        "_execute_web_fetch",
        "execute_web_fetch",
        "_perform_web_fetch",
        "perform_web_fetch",
        "_web_fetch",
        "web_fetch",
        "_run_web_search",
        "run_web_search",
    )

    for name in bool_route_names:
        if _nova_attachment_guard_wrap_module_bool_route(name):
            wrapped_bool_methods.append(name)

    for name in result_route_names:
        if _nova_attachment_guard_wrap_module_result_route(name):
            wrapped_result_methods.append(name)

    # Also wrap service classes. The regression suite monkeypatches fake classes
    # onto this module and expects installer() to wrap those class methods too.
    for object_name, value in list(globals().items()):
        if not isinstance(value, type):
            continue

        for method_name in bool_route_names:
            if _nova_attachment_guard_wrap_class_bool_route(value, method_name):
                wrapped_bool_methods.append(f"{object_name}.{method_name}")

        for method_name in result_route_names:
            if _nova_attachment_guard_wrap_class_result_route(value, method_name):
                wrapped_result_methods.append(f"{object_name}.{method_name}")

    wrapped = list(wrapped_bool_methods) + list(wrapped_result_methods)

    return {
        "ok": True,
        "installed": True,
        "wrapped": wrapped,
        "wrapped_bool_methods": wrapped_bool_methods,
        "wrapped_result_methods": wrapped_result_methods,
    }


def _nova_install_attachment_guard_web_suppression():
    return _nova_attachment_guard_install_web_routing_suppression()


try:
    _nova_attachment_guard_install_web_routing_suppression()
except Exception:
    pass

# NOVA_CHAT_SERVICE_ATTACHMENT_WEB_SUPPRESSION_RESULT_WRAP_V3_20260705
def _nova_attachment_guard_method_looks_like_bool_web_route(name):
    lowered = str(name or "").lower()

    return (
        "web" in lowered
        and (
            lowered.startswith("_should")
            or lowered.startswith("should")
            or lowered.startswith("_needs")
            or lowered.startswith("needs")
            or lowered.startswith("_route")
            or lowered.startswith("route")
        )
    )

def install_attachment_web_suppression():
    return _nova_attachment_guard_install_web_routing_suppression()