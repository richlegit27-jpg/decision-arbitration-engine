from __future__ import annotations

import traceback
from typing import Any, Callable, Tuple

from flask import jsonify

from nova_backend.utils.api_response import error_response


def guarded_json_route(fn: Callable[..., Tuple[dict, int] | dict]):
    def wrapper(*args: Any, **kwargs: Any):
        try:
            result = fn(*args, **kwargs)

            if isinstance(result, tuple) and len(result) == 2:
                payload, status = result
                return jsonify(payload), int(status)

            return jsonify(result), 200

        except Exception as e:
            return jsonify(
                error_response(
                    error=str(e),
                    code="unhandled_exception",
                    meta={
                        "traceback": traceback.format_exc(limit=8),
                        "route": getattr(fn, "__name__", "unknown_route"),
                    },
                )
            ), 500

    wrapper.__name__ = getattr(fn, "__name__", "guarded_route")
    wrapper.__doc__ = getattr(fn, "__doc__", "")
    return wrapper