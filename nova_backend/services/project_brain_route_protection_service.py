from __future__ import annotations

import json


def response_owned_by_project_brain(response) -> bool:
    try:
        payload = json.loads(
            response.get_data(as_text=True)
        )

        debug = (
            payload.get("debug")
            or {}
        )

        route = str(
            debug.get("route")
            or debug.get("route_taken")
            or ""
        ).strip()

        return route == "project_brain_general_intelligence"

    except Exception:
        return False