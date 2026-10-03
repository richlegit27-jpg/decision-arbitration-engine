from __future__ import annotations


def image_generation_failure_message(error: Exception) -> str:
    """Map known image-provider failures to safe, user-facing copy."""
    details = [str(error or ""), type(error).__name__]
    status = getattr(error, "status_code", None)
    code = getattr(error, "code", None)
    body = getattr(error, "body", None)
    response = getattr(error, "response", None)

    if status is None and response is not None:
        status = getattr(response, "status_code", None)
    if not body and response is not None:
        body = getattr(response, "text", None)

    details.extend((str(code or ""), str(body or "")))
    diagnostic = " ".join(details).lower()

    safety_markers = (
        "moderation_blocked",
        "safety_violations",
        "safety_violation",
        "content_policy_violation",
        "content_policy",
        "moderation",
    )
    if any(marker in diagnostic for marker in safety_markers):
        return (
            "Nova couldn't generate that image because the request was blocked "
            "by the image safety system. Try changing the description and "
            "generate it again."
        )

    try:
        status = int(status) if status is not None else None
    except (TypeError, ValueError):
        status = None

    error_name = type(error).__name__.lower()
    if status == 429 or "ratelimit" in error_name or "rate_limit" in diagnostic:
        return (
            "Nova couldn't generate the image right now because the image "
            "service is receiving too many requests. Please wait a moment "
            "and try again."
        )

    if status in (401, 403) or any(
        marker in diagnostic
        for marker in ("authenticationerror", "invalid_api_key", "unauthorized", "permissiondenied")
    ):
        return (
            "Nova couldn't generate the image because the image service's "
            "authentication or configuration needs attention."
        )

    if isinstance(error, TimeoutError) or "timeout" in error_name or "timed out" in diagnostic:
        return "The image generation request timed out. Please try again."

    if (status is not None and status >= 500) or any(
        marker in diagnostic
        for marker in ("apiconnectionerror", "connectionerror", "serviceunavailable", "temporarily unavailable")
    ):
        return "Nova couldn't reach the image service right now. Please try again shortly."

    return "Nova couldn't generate that image. Please adjust the description or try again later."
