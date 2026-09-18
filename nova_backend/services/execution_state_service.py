from __future__ import annotations

import json
from pathlib import Path


class ExecutionStateService:

    def __init__(self, session_service=None):
        self.session_service = session_service
        self.active_execution_cache = {}
        self.completed_execution_cache = {}

        self.status_questions = {
            "status",
            "what is the status",
            "current status",
            "where are we",
            "what's the status",
            "whats the status",
        }

    def clean_text(self, value):
        return " ".join(str(value or "").strip().lower().split())

    def is_status_question(self, user_text):
        clean = self.clean_text(user_text).strip(" .!")
        return clean in self.status_questions

    def execution_is_active(self, execution):
        if not isinstance(execution, dict):
            return False

        goal = str(execution.get("goal") or "").strip()
        status = str(execution.get("status") or "").strip().lower()

        if not goal:
            return False

        if status in {
            "complete",
            "completed",
            "done",
            "failed",
            "error",
            "cancelled",
            "canceled",
        }:
            return False

        return True

    def execution_is_complete(self, execution):
        if not isinstance(execution, dict):
            return False

        goal = str(execution.get("goal") or "").strip()
        status = str(execution.get("status") or "").strip().lower()

        if not goal:
            return False

        if execution.get("complete") is True:
            return True

        return status in {
            "complete",
            "completed",
            "done",
        }

    def goal(self, execution):
        return str((execution or {}).get("goal") or "").strip()

    def steps(self, execution):
        raw_steps = (execution or {}).get("steps") or []

        if not isinstance(raw_steps, list):
            return []

        steps = []

        for item in raw_steps:
            if isinstance(item, dict):
                step = dict(item)

                if not step.get("title"):
                    step["title"] = str(
                        step.get("text")
                        or step.get("name")
                        or ""
                    ).strip()

                if step.get("title"):
                    steps.append(step)

            else:
                title = str(item or "").strip()

                if title:
                    steps.append(
                        {
                            "title": title,
                            "action": "unknown",
                            "status": "pending",
                        }
                    )

        return steps
    def index(self, execution, steps):
        value = (
            (execution or {}).get("current_index")
            if "current_index" in (execution or {})
            else (execution or {}).get("current_step_index", 0)
        )

        try:
            index = int(value or 0)
        except Exception:
            index = 0

        if steps:
            index = max(
                0,
                min(index, len(steps) - 1)
            )
        else:
            index = max(
                0,
                index
            )

        return index
    def current_step(self, execution):
        steps = self.steps(execution)
        index = self.index(execution, steps)

        current = str(
            (execution or {}).get("current_step") or ""
        ).strip()

        if current:
            return current

        if steps and 0 <= index < len(steps):
            step = steps[index]

            if isinstance(step, dict):
                return step.get("title") or step.get("text") or ""

            return str(step)

        return ""
    def execution_status_text(self, execution):
        goal = self.goal(execution)

        status = str(
            (execution or {}).get("status") or "ready"
        ).strip() or "ready"

        steps = self.steps(execution)
        index = self.index(execution, steps)
        current_step = self.current_step(execution)

        lines = [
            f"Active mission: {goal}",
            f"Status: {status}",
        ]

        if current_step and steps:
            lines.append(
                f"Step {index + 1}/{len(steps)}: {current_step}"
            )
        elif current_step:
            lines.append(
                f"Current step: {current_step}"
            )

        if str(
            (execution or {}).get("waiting") or ""
        ).lower() in {
            "true",
            "1",
            "yes",
        }:
            lines.append(
                "Next: send next, k, continue, or run it to advance."
            )

        return "\n".join(lines).strip()
    def read_sessions_file(self):
        path = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "sessions.json"
        )

        if not path.exists():
            return {}, path

        try:
            data = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

            return data, path

        except Exception:
            return {}, path
    def find_session(self, container, session_id):
        if not session_id:
            return None

        if isinstance(container, dict):

            if str(container.get("id") or "") == str(session_id):
                return container

            direct = container.get(session_id)

            if isinstance(direct, dict):
                return direct

            for key in (
                "sessions",
                "items",
                "data",
            ):
                found = self.find_session(
                    container.get(key),
                    session_id,
                )

                if found is not None:
                    return found

            for value in container.values():
                if isinstance(value, (dict, list)):
                    found = self.find_session(
                        value,
                        session_id,
                    )

                    if found is not None:
                        return found

        elif isinstance(container, list):

            for item in container:
                found = self.find_session(
                    item,
                    session_id,
                )

                if found is not None:
                    return found

        return None
    def get_working_state(
        self,
        session_id,
    ):
        if not session_id:
            return {}

        session = None
        services = []

        if self.session_service is not None:
            services.append(
                self.session_service
            )

        for svc in services:
            for method_name in (
                "get_session",
                "get",
            ):
                method = getattr(
                    svc,
                    method_name,
                    None,
                )

                if not callable(method):
                    continue

                try:
                    session = method(session_id)
                except Exception:
                    session = None

                if isinstance(session, dict):
                    break

            if isinstance(session, dict):
                break

        if not isinstance(session, dict):
            sessions_data, _path = self.read_sessions_file()

            session = self.find_session(
                sessions_data,
                session_id,
            )

        if not isinstance(session, dict):
            return {}

        state = session.get(
            "working_state"
        )

        if not isinstance(state, dict):
            state = {}

        for key in (
            "active_execution",
            "execution_state",
            "execution",
            "last_execution",
        ):
            if key in session and key not in state:
                state[key] = session.get(key)

        return state
    def persist_working_state(
        self,
        session_id,
        patch,
    ):
        session_id = str(session_id or "").strip()

        if not session_id or not isinstance(patch, dict):
            return False

        service_saved = False

        svc = self.session_service

        method = getattr(
            svc,
            "update_working_state",
            None,
        )

        if callable(method):
            try:
                method(
                    session_id,
                    patch,
                )
                service_saved = True

            except Exception:
                service_saved = False

        data, path = self.read_sessions_file()

        if data is None:
            return service_saved

        session = self.find_session(
            data,
            session_id,
        )

        if not isinstance(session, dict):
            session = {
                "id": session_id,
                "title": session_id,
                "messages": [],
                "session_attachments": [],
                "working_state": {},
                "active_execution": None,
                "execution_state": None,
            }

            if isinstance(data, dict):
                sessions_value = data.get("sessions")

                if isinstance(sessions_value, list):
                    sessions_value.append(session)

                elif isinstance(sessions_value, dict):
                    sessions_value[session_id] = session

                else:
                    data[session_id] = session

            elif isinstance(data, list):
                data.append(session)

            else:
                return service_saved

        state = session.get("working_state")

        if not isinstance(state, dict):
            state = {}

        state.update(patch)

        session["working_state"] = state

        if "active_execution" in patch:
            session["active_execution"] = patch.get(
                "active_execution"
            )

        if "execution_state" in patch:
            session["execution_state"] = patch.get(
                "execution_state"
            )

        try:
            path.write_text(
                json.dumps(
                    data,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            return True

        except Exception:
            return service_saved
    def get_execution_state(
        self,
        session_id,
    ):
        session_id = str(
            session_id or ""
        ).strip()

        if not session_id:
            return {}

        state = self.get_working_state(
            session_id
        ) or {}

        if not state:
            try:
                session = self.session_service.get_session(
                    session_id
                )

                if isinstance(session, dict):
                    state = {
                        "execution_state": session.get("execution_state"),
                        "active_execution": session.get("active_execution"),
                        "execution": session.get("execution"),
                        "last_execution": session.get("last_execution"),
                    }

            except Exception:
                state = {}

        execution = (
            state.get("execution_state")
            or state.get("active_execution")
            or state.get("execution")
            or state.get("last_execution")
        )

        if isinstance(execution, dict) and execution:
            return execution

        return {}
    def save_execution_state(
        self,
        session_id,
        execution_state=None,
    ):
        session_id = str(session_id or "").strip()

        if not session_id:
            return {}

        if not isinstance(execution_state, dict):
            return {}

        incoming = dict(execution_state)

        incoming_steps = incoming.get("steps")

        if not isinstance(incoming_steps, list):
            incoming_steps = []

        incoming["steps"] = [
            dict(step) if isinstance(step, dict) else step
            for step in incoming_steps
        ]

        raw_index = incoming.get("current_index")

        if raw_index is None:
            raw_index = incoming.get(
                "current_step_index",
                0,
            )

        try:
            incoming_index = int(raw_index)
        except (TypeError, ValueError):
            incoming_index = 0

        incoming_index = max(
            0,
            incoming_index,
        )

        complete = (
            incoming.get("complete") is True
            or str(
                incoming.get("status") or ""
            ).strip().lower()
            in {
                "complete",
                "completed",
                "done",
            }
        )

        if complete:
            incoming_index = max(
                incoming_index,
                len(incoming["steps"]),
            )

        elif incoming["steps"]:
            incoming_index = min(
                incoming_index,
                len(incoming["steps"]) - 1,
            )

        incoming["current_index"] = incoming_index
        incoming["current_step_index"] = incoming_index

        self.active_execution_cache[session_id] = incoming

        self.persist_working_state(
            session_id,
            {
                "active_execution": incoming,
                "execution_state": incoming,
            },
        )

        return incoming
    def get_active_execution(self, session_id):
        session_id = str(session_id or "").strip()

        if not session_id:
            return None

        cached = self.active_execution_cache.get(session_id)

        if self.execution_is_active(cached):
            return cached

        state = self.get_working_state(
            session_id
        ) or {}

        for key in (
            "active_execution",
            "execution_state",
            "execution",
        ):
            execution = state.get(key)

            if self.execution_is_active(execution):
                self.active_execution_cache[session_id] = execution
                return execution

        return None
    def get_completed_execution(self, session_id):
        session_id = str(session_id or "").strip()

        if not session_id:
            return None

        cached = self.completed_execution_cache.get(
            session_id
        )

        if self.execution_is_complete(cached):
            return cached

        state = self.get_working_state(
            session_id
        ) or {}

        for key in (
            "last_execution",
            "execution_state",
            "execution",
            "active_execution",
        ):
            execution = state.get(key)

            if self.execution_is_complete(execution):
                self.completed_execution_cache[session_id] = execution
                return execution

        return None


    def completed_status_text(self, execution):
        if not isinstance(execution, dict):
            return ""

        goal = self.goal(execution)

        return (
            f"Completed mission: {goal}"
            if goal
            else "No completed mission."
        )


