from functools import wraps
import traceback
from typing import Any, Callable, Tuple

from flask import jsonify, request
from nova_backend.utils.api_response import error_response


def guarded_json_route(fn: Callable[..., Tuple[dict, int] | dict]):

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any):

        print(
            "[ROUTE GUARD DEBUG BEFORE]",
            {
                "route": getattr(
                    fn,
                    "__name__",
                    "unknown",
                ),
                "content_type": getattr(
                    request,
                    "content_type",
                    None,
                ),
                "raw": request.get_data(
                    cache=True,
                    as_text=True,
                ),
            },
        )

        try:
            result = fn(*args, **kwargs)

            print(
                "[ROUTE GUARD DEBUG AFTER]",
                getattr(
                    fn,
                    "__name__",
                    "unknown",
                ),
            )

            if isinstance(result, tuple) and len(result) == 2:
                payload, status = result
                return jsonify(payload), int(status)

            return jsonify(result), 200

        except Exception as e:
            print(
                "[ROUTE GUARD DEBUG ERROR]",
                str(e),
            )

            return jsonify(
                error_response(
                    error=str(e),
                    code="unhandled_exception",
                    meta={
                        "traceback": traceback.format_exc(limit=8),
                        "route": getattr(
                            fn,
                            "__name__",
                            "unknown_route",
                        ),
                    },
                )
            ), 500

    return wrapper