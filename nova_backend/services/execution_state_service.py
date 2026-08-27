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

            if str(container.get("id") or "") == session_id:
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
                        for state_key, state_value in state.items():

                            if state_key in {
                                "active_execution",
                                "execution_state",
                                "execution",
                                "last_execution",
                            } and state_value is None:
                                merged_state[state_key] = None
                                continue

                            if (
                                state_key not in merged_state
                                or state_value is not None
                            ):
                                merged_state[state_key] = state_value

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



                    if isinstance(
                        working_state,
                        dict,
                    ):

                        for ws_key, ws_value in working_state.items():

                            if ws_key in {
                                "active_execution",
                                "execution_state",
                                "execution",
                                "last_execution",
                            }:

                                if isinstance(
                                    ws_value,
                                    dict,
                                ) and ws_value:

                                    merged_state[ws_key] = ws_value

                                continue

                            merged_state[ws_key] = ws_value

                    for key in (
                        "active_execution",
                        "execution_state",
                        "execution",
                        "last_execution",
                    ):

                        value = session.get(
                            key
                        )

                        if isinstance(value, dict) and value:
                            merged_state[key] = value

                        if key in session and value is None:
                            merged_state[key] = None
                            continue

                        if isinstance(value, dict) and value:

                            if value.get(
                                "status"
                            ) == "complete":

                                merged_state[key] = None
                                continue

                            existing = merged_state.get(
                                key
                            )
                            existing_index = 0
                            value_index = 0

                            if isinstance(existing, dict):
                                existing_index = int(
                                    existing.get(
                                        "current_index"
                                    )
                                    or existing.get(
                                        "current_step_index"
                                    )
                                    or 0
                                )

                            value_index = int(
                                value.get(
                                    "current_index"
                                )
                                or value.get(
                                    "current_step_index"
                                )
                                or 0
                            )

                            def execution_richness(item):
                                score = 0

                                if not isinstance(item, dict):
                                    return score

                                steps = item.get("steps")

                                if isinstance(steps, list):
                                    score += len(steps)

                                    for step in steps:
                                        if isinstance(step, dict):
                                            if step.get("action"):
                                                score += 5

                                            if step.get("result"):
                                                score += 5

                                            if step.get("text"):
                                                score += 3

                                            if step.get("target_file"):
                                                score += 3

                                            if step.get("target_function"):
                                                score += 3

                                            if step.get("mutation_mode"):
                                                score += 3

                                            if step.get("mutation_ready"):
                                                score += 20

                                            if step.get("next_action") in {
                                                "generate_file_replacement",
                                                "generate_function_replacement",
                                            }:
                                                score += 20

                                            if step.get("payload_required"):
                                                score += 5

                                if item.get("history"):
                                    score += 2

                                if item.get("learning_history"):
                                    score += 2

                                return score

                            existing_richness = execution_richness(
                                existing
                            )

                            value_richness = execution_richness(
                                value
                            )

                            print(
                                "DEBUG EXECUTION MERGE RICHNESS:",
                                {
                                    "key": key,
                                    "existing": existing_richness,
                                    "incoming": value_richness,
                                    "existing_index": existing_index,
                                    "value_index": value_index,
                                },
                            )

                            if value is None:
                                merged_state[key] = None

                            elif (
                                not existing
                                or value_index > existing_index
                                or (
                                    value_index == existing_index
                                    and value_richness >= existing_richness
                                )
                            ):
                                merged_state[key] = value

        data, _ = self.read_sessions_file()

        session = self.find_session(
            data,
            session_id,
        )

        print(
            "DEBUG FOUND SESSION:",
            session_id,
            isinstance(session, dict),
            list(session.keys())
            if isinstance(session, dict)
            else session,
        )

        if isinstance(session, dict):

            working_state = session.get(
                "working_state"
            )

            print(
                "DEBUG WORKING STATE EXEC:",
                {
                    "active_execution": working_state.get(
                        "active_execution"
                    ),
                    "execution_state": working_state.get(
                        "execution_state"
                    ),
                },
            )

            for ws_key, ws_value in working_state.items():
                if ws_key in {
                    "active_execution",
                    "execution_state",
                    "execution",
                    "last_execution",
                }:

                    if ws_key in working_state and ws_value is None:
                        merged_state[ws_key] = None
                        continue

                    if isinstance(ws_value, dict) and ws_value:
                        merged_state[ws_key] = ws_value

                    continue

                merged_state[ws_key] = ws_value

            for key in (
                "active_execution",
                "execution_state",
                "execution",
                "last_execution",
            ):

                value = session.get(
                    key
                )

                if key in session and value is None:
                    merged_state[key] = None
                    continue

                if isinstance(value, dict) and value:

                    existing = merged_state.get(
                        key
                    )

                    existing_index = 0
                    value_index = 0

                    if isinstance(existing, dict):

                        existing_index = int(
                            existing.get(
                                "current_index"
                            )
                            or existing.get(
                                "current_step_index"
                            )
                            or 0
                        )

                    value_index = int(
                        value.get(
                            "current_index"
                        )
                        or value.get(
                            "current_step_index"
                        )
                        or 0
                    )

                    if (
                        not existing
                        or value_index >= existing_index
                    ):
                        merged_state[key] = value


        print(
            "DEBUG WORKING STATE EXECUTION RETURN:",
            {
                "active_status": (
                    merged_state.get("active_execution", {}).get("status")
                    if isinstance(
                        merged_state.get("active_execution"),
                        dict,
                    )
                    else None
                ),
                "active_index": (
                    merged_state.get("active_execution", {}).get("current_index")
                    if isinstance(
                        merged_state.get("active_execution"),
                        dict,
                    )
                    else None
                ),
                "state_status": (
                    merged_state.get("execution_state", {}).get("status")
                    if isinstance(
                        merged_state.get("execution_state"),
                        dict,
                    )
                    else None
                ),
                "state_index": (
                    merged_state.get("execution_state", {}).get("current_index")
                    if isinstance(
                        merged_state.get("execution_state"),
                        dict,
                    )
                    else None
                ),
            },
        )

        return merged_state

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

        print(
            "DEBUG SAVE FOUND SESSION:",
            {
                "session_id": session_id,
                "found": isinstance(session, dict),
                "keys": (
                    list(session.keys())
                    if isinstance(session, dict)
                    else []
                ),
            },
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

                sessions_value = data.get(
                    "sessions"
                )

                if isinstance(sessions_value, list):
                    sessions_value.append(
                        session
                    )

                elif isinstance(sessions_value, dict):
                    sessions_value[session_id] = session

                else:
                    data[session_id] = session

            elif isinstance(data, list):
                data.append(
                    session
                )

            else:
                return service_saved

        state = session.get(
            "working_state"
        )

        if not isinstance(state, dict):
            state = {}

        state.update(
            patch
        )

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

            print(
                "DEBUG WORKING STATE WRITTEN:",
                session_id,
                list(
                    patch.keys()
                ),
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

        print(
            "DEBUG GET EXECUTION STATE INPUT:",
            {
                "session_id": session_id,
                "keys": list(
                    state.keys()
                ),
            },
        )

        execution = state.get(
            "execution_state"
        )

        if (
            isinstance(execution, dict)
            and execution
        ):
            print(
                "DEBUG EXECUTION RETURN execution_state:",
                {
                    "status": execution.get("status"),
                    "current_index": execution.get("current_index"),
                    "steps": execution.get("steps"),
                },
            )

            return execution

        execution = state.get(
            "active_execution"
        )

        if (
            isinstance(execution, dict)
            and execution
        ):
            print(
                "DEBUG EXECUTION RETURN active_execution:",
                {
                    "status": execution.get("status"),
                    "current_index": execution.get("current_index"),
                    "steps": execution.get("steps"),
                },
            )

            return execution

        print(
            "DEBUG EXECUTION EMPTY:",
            session_id,
        )

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

        print(
            "DEBUG SAVE EXECUTION INCOMING:",
            {
                "status": execution_state.get("status"),
                "current_index": execution_state.get("current_index"),
                "complete": execution_state.get("complete"),
                "updated_at": execution_state.get("updated_at"),
            },
        )

        # NORMALIZE EXECUTION STATE FORMAT
        execution_state["current_step_index"] = execution_state.get(
            "current_index",
            execution_state.get(
                "current_step_index",
                0,
            ),
        )

        execution_state["current_index"] = execution_state.get(
            "current_step_index",
            0,
        )

        from datetime import datetime, timezone

        execution_state["updated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        print(
            "DEBUG SAVE EXECUTION STATE:",
            {
                "session_id": session_id,
                "goal": execution_state.get("goal"),
                "status": execution_state.get("status"),
                "current_index": execution_state.get("current_index"),
                "steps": execution_state.get("steps"),
            },
        )

        if not execution_state:
            return {}

        if (
            not execution_state.get("steps")
            and not execution_state.get("plan")
            and not execution_state.get("goal")
        ):
            return {}

        execution_state["_execution_processing"] = False
        execution_state["lock"] = False

        self.active_execution_cache[session_id] = (
            execution_state
        )

        print(
            "DEBUG BEFORE PERSIST EXECUTION:",
            {
                "status": execution_state.get("status"),
                "current_index": execution_state.get("current_index"),
                "current_step_index": execution_state.get("current_step_index"),
                "goal": execution_state.get("goal"),
            },
        )

        self.persist_working_state(
            session_id,
            {
                "execution_state": execution_state,
                "active_execution": execution_state,
            },
        )

        return execution_state

    def get_active_execution(self, session_id):
        session_id = str(session_id or "").strip()

        if not session_id:
            return None

        cached = self.active_execution_cache.get(
            session_id
        )

        print(
            "DEBUG ACTIVE EXEC CACHE:",
            session_id,
            cached,
        )

        if self.execution_is_active(cached):
            print(
                "DEBUG ACTIVE EXEC RETURN CACHE"
            )
            return cached

        state = self.get_working_state(
            session_id
        ) or {}

        print(
            "DEBUG GET EXECUTION STATE:",
            {
                "session": session_id,
                "cache": self.active_execution_cache.get(
                    session_id
                ),
                "working_state": state,
            },
        )

        print(
            "DEBUG ACTIVE EXEC WORKING STATE:",
            session_id,
            state,
        )

        for key in (
            "active_execution",
            "execution_state",
            "execution",
        ):
            execution = state.get(key)

            print(
                "DEBUG ACTIVE EXEC CHECK:",
                key,
                execution,
            )

            if isinstance(execution, dict) and execution:

                print(
                    "DEBUG ACTIVE EXEC RETURN:",
                    key,
                )

                self.active_execution_cache[
                    session_id
                ] = execution

                return execution

        print(
            "DEBUG ACTIVE EXEC NONE FOUND:",
            session_id,
        )

        return None

    def get_completed_execution(self, session_id):
        session_id = str(session_id or "").strip()

        if session_id:
            cached = self.completed_execution_cache.get(session_id)

            if self.execution_is_complete(cached):
                return cached

        state = self.get_working_state(session_id) or {}



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

        return ""