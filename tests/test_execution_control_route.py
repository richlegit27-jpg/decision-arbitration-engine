from flask import Flask

from nova_backend.services.execution_route_service import (
    ExecutionRouteService,
)
from nova_backend.services.execution_service import ExecutionService


class _WorkingStateStore:
    def __init__(self):
        self.state = {}

    def get_working_state(self, session_id):
        return self.state.get(session_id, {})

    def update_working_state(self, session_id, patch):
        current = dict(self.state.get(session_id, {}))
        current.update(patch)
        self.state[session_id] = current
        return current


def test_execution_control_runs_and_persists_a_normalized_step():
    flask_app = Flask(__name__)
    store = _WorkingStateStore()
    route = ExecutionRouteService(
        working_state_service=store,
        execution_service=ExecutionService(),
    )

    with flask_app.test_request_context(
        "/api/execution/control",
        method="POST",
        json={"session_id": "execution-control-test", "action": "run_step"},
    ):
        response = route.execution_control()

    payload = response.get_json()
    execution = payload["execution_state"]

    assert response.status_code == 200
    assert payload["ok"] is True
    assert execution["status"] == "completed"
    assert execution["steps"][0]["status"] == "completed"
    assert store.state["execution-control-test"]["execution"] == execution


def test_execution_control_reports_missing_dependencies():
    flask_app = Flask(__name__)
    route = ExecutionRouteService()

    with flask_app.test_request_context(
        "/api/execution/control",
        method="POST",
        json={"session_id": "execution-control-test", "action": "run_step"},
    ):
        response, status = route.execution_control()

    assert status == 503
    assert response.get_json()["error"] == "execution control is unavailable"
