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
        steps = []

        for item in raw_steps:
            if isinstance(item, dict):
                title = str(
                    item.get("title")
                    or item.get("text")
                    or item.get("name")
                    or ""
                ).strip()
            else:
                title = str(item or "").strip()

            if title:
                steps.append(title)

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
            index = max(0, min(index, len(steps) - 1))
        else:
            index = max(0, index)

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
            return steps[index]

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
            / "nova_sessions.json"
        )

        if not path.exists():
            return None, path

        try:
            return (
                json.loads(
                    path.read_text(
                        encoding="utf-8",
                        errors="replace",
                    )
                ),
                path,
            )
        except Exception:
            return None, path

    def find_session(self, container, session_id):
        if not session_id:
            return None

        if isinstance(container, dict):
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
                if isinstance(value, dict):
                    if str(value.get("id") or "") == session_id:
                        return value

                if isinstance(value, (dict, list)):
                    found = self.find_session(
                        value,
                        session_id,
                    )

                    if found is not None:
                        return found

        if isinstance(container, list):
            for item in container:
                if isinstance(item, dict):
                    if str(item.get("id") or "") == session_id:
                        return item

        return None

    def get_working_state(self, session_id):
        session_id = str(session_id or "").strip()

        if not session_id:
            return {}

        merged_state = {}

        svc = self.session_service

        if svc is not None:

            method = getattr(
                svc,
                "get_working_state",
                None,
            )

            if callable(method):
                try:
                    state = method(session_id)

                    if isinstance(state, dict):
                        merged_state.update(state)

                except Exception:
                    pass

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

                    working_state = session.get(
                        "working_state"
                    )

                    if isinstance(working_state, dict):
                        merged_state.update(
                            working_state
                        )

                    for key in (
                        "active_execution",
                        "execution_state",
                        "execution",
                    ):
                        value = session.get(key)

                        if isinstance(value, dict):
                            merged_state[key] = value

        data, _ = self.read_sessions_file()

        session = self.find_session(
            data,
            session_id,
        )

        if isinstance(session, dict):

            working_state = session.get(
                "working_state"
            )

            if isinstance(working_state, dict):
                merged_state.update(
                    working_state
                )

            for key in (
                "active_execution",
                "execution_state",
                "execution",
            ):
                value = session.get(key)

                if isinstance(value, dict):
                    merged_state[key] = value

        return merged_state

    def persist_working_state(self, session_id, patch):
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

    def get_active_execution(self, session_id):
        session_id = str(session_id or "").strip()

        if session_id:
            cached = self.active_execution_cache.get(
                session_id
            )

            if self.execution_is_active(cached):
                return cached

        state = self.get_working_state(session_id)

        for key in (
            "active_execution",
            "execution_state",
            "execution",
        ):
            execution = state.get(key)

            if self.execution_is_active(execution):
                if session_id:
                    self.active_execution_cache[session_id] = execution

                return execution

        return None

    def get_completed_execution(self, session_id):
        session_id = str(session_id or "").strip()

        if session_id:
            cached = self.completed_execution_cache.get(session_id)

            if self.execution_is_complete(cached):
                return cached

        state = self.get_working_state(session_id)

        for key in (
            "execution_state",
            "execution",
            "last_execution",
        ):
            execution = state.get(key)

            if self.execution_is_complete(execution):
                if session_id:
                    self.completed_execution_cache[session_id] = execution

                return execution

        return None


    def completed_status_text(self, execution):
        goal = self.goal(execution)

        if goal:
            return (
                f"No active mission is running. "
                f"Last completed mission: {goal}"
            )

        return "No active mission is running."


    def persist_execution(self, session_id, execution):
        session_id = str(session_id or "").strip()

        if self.execution_is_complete(execution):

            if session_id:
                self.active_execution_cache.pop(
                    session_id,
                    None,
                )

                self.completed_execution_cache[
                    session_id
                ] = execution

            return self.persist_working_state(
                session_id,
                {
                    "active_execution": None,
                    "execution_state": execution,
                    "active_task": "",
                    "next_move": "",
                    "checkpoint": "Execution mission complete",
                },
            )


        if not self.execution_is_active(execution):
            return False


        if session_id:
            self.active_execution_cache[
                session_id
            ] = execution


        goal = self.goal(execution)

        current_step = self.current_step(
            execution
        )


        patch = {
            "active_execution": execution,
            "execution_state": execution,
            "active_task": goal,
            "next_move": current_step,
            "checkpoint": "Active execution mission",
        }


        return self.persist_working_state(
            session_id,
            patch,
        )

