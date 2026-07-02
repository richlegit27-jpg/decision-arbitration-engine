
import json

from nova_backend.services.project_brain_api_finalizer import (
    STATE_RECALL_REFRESH_HOOK_NAME,
    install_project_brain_state_recall_refresh_finalizer,
)


class FakeApp:
    def __init__(self):
        self.after_request_funcs = {None: []}


class FakeResponse:
    def __init__(self, data, content_type="application/json"):
        self.headers = {"Content-Type": content_type}
        self._data = data.encode("utf-8") if isinstance(data, str) else data

    def get_data(self, as_text=False):
        if as_text:
            return self._data.decode("utf-8")
        return self._data

    def set_data(self, value):
        self._data = value.encode("utf-8") if isinstance(value, str) else value


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def refresh_payload(payload):
    if payload.get("route") != "project_state_current_memory_direct_recall":
        return payload

    updated = dict(payload)
    updated["text"] = "Current Nova project state. Next move: Project Brain State Recall Refresh v1."
    updated["answer"] = updated["text"]
    updated["assistant_message"] = {
        "text": updated["text"],
        "content": updated["text"],
    }
    return updated


def main():
    print("NOVA PROJECT BRAIN API FINALIZER SMOKE")
    print("======================================")

    app = FakeApp()

    def existing_hook(response):
        return response

    existing_hook.__name__ = "existing_hook"
    app.after_request_funcs[None].append(existing_hook)

    result = install_project_brain_state_recall_refresh_finalizer(
        app,
        refresh_project_state_payload=refresh_payload,
    )

    assert_true("installer result", result["installed"] is True, result)
    assert_true("hook inserted first", app.after_request_funcs[None][0].__name__ == STATE_RECALL_REFRESH_HOOK_NAME, app.after_request_funcs)
    assert_true("existing hook preserved", app.after_request_funcs[None][1].__name__ == "existing_hook", app.after_request_funcs)

    second = install_project_brain_state_recall_refresh_finalizer(
        app,
        refresh_project_state_payload=refresh_payload,
    )

    names = [func.__name__ for func in app.after_request_funcs[None]]
    assert_true("installer idempotent", names.count(STATE_RECALL_REFRESH_HOOK_NAME) == 1, names)
    assert_true("hook still final order", names[0] == STATE_RECALL_REFRESH_HOOK_NAME, names)
    assert_true("second install result", second["installed"] is True, second)

    response = FakeResponse(json.dumps({
        "route": "project_state_current_memory_direct_recall",
        "text": "Next move: Start Project Brain cleanup/consolidation",
    }))

    hook = app.after_request_funcs[None][0]
    refreshed_response = hook(response)
    refreshed = json.loads(refreshed_response.get_data(as_text=True))

    assert_true("response refreshed", "Project Brain State Recall Refresh v1" in refreshed["text"], refreshed)
    assert_true("content length set", "Content-Length" in refreshed_response.headers, refreshed_response.headers)

    normal_response = FakeResponse(json.dumps({
        "route": "chat",
        "text": "normal chat",
    }))

    normal_raw_before = normal_response.get_data(as_text=True)
    normal_after = hook(normal_response)
    assert_true("normal response untouched", normal_after.get_data(as_text=True) == normal_raw_before, normal_after.get_data(as_text=True))

    html_response = FakeResponse("<html></html>", content_type="text/html")
    html_after = hook(html_response)
    assert_true("html response untouched", html_after.get_data(as_text=True) == "<html></html>", html_after.get_data(as_text=True))

    print("")
    print("NOVA PROJECT BRAIN API FINALIZER SMOKE PASSED")


if __name__ == "__main__":
    main()
