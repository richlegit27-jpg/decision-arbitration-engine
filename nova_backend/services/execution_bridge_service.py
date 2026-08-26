
from typing import Any

from nova_backend.services.project_brain_context_builder import (
    build_project_brain_context,
)


class ExecutionBridgeService:

    def __init__(
        self,
        chat_execution_service,
        logger,
        chat_service=None,
    ):
        self.chat_execution_service = chat_execution_service
        self.logger = logger
        self.chat_service = chat_service

    def try_execution_trigger(
        self,
        session_id,
        user_text,
    ):

        try:
            if not self.chat_execution_service.is_execution_trigger(
                user_text
            ):
                return None

            if hasattr(
                self.chat_execution_service,
                "execution_orchestrator_service",
            ):
                return None

            state = self.chat_execution_service.advance(
                session_id
            )
            reply_text = (
                self._format_execution_response(state)
                if hasattr(
                    self,
                    "_format_execution_response",
                )
                else self.chat_execution_service.format_reply(
                    state
                )
            )

            return {
                "ok": True,
                "skip_cleanup": True,
                "skip_post_processing": True,
                "skip_rewrite": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply_text,
                    "content": reply_text,
                    "execution_state": state,
                },
                "execution_state": state,
            }

        except Exception as exc:
            if self.logger:
                self.logger.exception(
                    "[NovaExecutionBridge] failed"
                )

            reply_text = (
                "Execution bridge failed: "
                + str(exc)
            )

            return {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply_text,
                    "content": reply_text,
                },
            }

    def try_execution_autoplan_start(
        self,
        session_id,
        user_text,
    ):
        print(
            "DEBUG NEW AUTOPLAN BRIDGE LOADED",
            flush=True,
        )
        try:
            clean = str(user_text or "").strip()
            lower = clean.lower()

            prefixes = [
                "auto-plan ",
                "autoplan ",
                "auto plan ",
            ]

            matched_prefix = None

            for prefix in prefixes:
                if lower.startswith(prefix):
                    matched_prefix = prefix
                    break

            if not matched_prefix:
                return None

            goal = clean[len(matched_prefix):].strip()

            if not goal:
                goal = "Untitled mission"

            goal_lower = goal.lower()

            if (
                "flask api" in goal_lower
                and any(
                    word in goal_lower
                    for word in (
                        "repair",
                        "fix",
                        "debug",
                        "syntax",
                        "error",
                        "broken",
                    )
                )
            ):

                steps = [
                    {
                        "title": "Inspect Flask API failure",
                        "action": "test",
                        "target_file": "flask_api/app.py",
                    },
                    {
                        "title": "Repair Flask API",
                        "action": "implement",
                        "target_file": "flask_api/app.py",
                        "content": (
                            "from flask import Flask, jsonify\n\n"
                            "app = Flask(__name__)\n\n"
                            "@app.route('/health')\n"
                            "def health():\n"
                            "    return jsonify({'ok': True})\n\n"
                            "if __name__ == '__main__':\n"
                            "    app.run(debug=True)\n"
                        ),
                    },
                    {
                        "title": "Verify Flask API repair",
                        "action": "test",
                        "target_file": "flask_api/app.py",
                    },
                    {
                        "title": "Review repair result",
                        "action": "review",
                    },
                ]

            elif (
                "python project" in goal_lower
                or "create a small python" in goal_lower
            ):

                steps = [
                    {
                        "title": "Create Python project structure",
                        "action": "implement",
                        "target_file": "hello_nova/main.py",
                        "content": (
                            "def greet():\n"
                            "    return \"Hello Nova\"\n\n\n"
                            "if __name__ == \"__main__\":\n"
                            "    print(greet())\n"
                        ),
                    },
                    {
                        "title": "Run and verify Python project",
                        "action": "test",
                        "target_file": "hello_nova/main.py",
                    },
                    {
                        "title": "Review result and finalize",
                        "action": "review",
                    },
                ]

            elif "flask api" in goal_lower:
                steps = [
                    {
                        "title": "Create Flask API structure",
                        "action": "implement",
                        "target_file": "flask_api/app.py",
                        "content": (
                            "from flask import Flask, jsonify\n\n"
                            "app = Flask(__name__)\n\n"
                            "@app.route('/health')\n"
                            "def health():\n"
                            "    return jsonify({'ok': True})\n\n"
                            "if __name__ == '__main__':\n"
                            "    app.run(debug=True)\n"
                        ),
                    },
                    {
                        "title": "Run Flask API test",
                        "action": "test",
                        "target_file": "flask_api/app.py",
                    },
                    {
                        "title": "Review API result",
                        "action": "review",
                    },
                ]

            elif (
                "multi" in goal_lower
                or "import failure" in goal_lower
                or "dependency" in goal_lower
            ):

                steps = [
                    {
                        "title": "Inspect Python project failure",
                        "action": "test",
                        "target_file": "multi_test/app.py",
                        "target_files": [
                            "multi_test/app.py",
                            "multi_test/config.py",
                        ],
                    },
                    {
                        "title": "Repair Python dependency issue",
                        "action": "implement",
                        "target_file": "multi_test/app.py",
                        "target_files": [
                            "multi_test/app.py",
                            "multi_test/config.py",
                        ],
                        "mutation_mode": "file",
                    },
                    {
                        "title": "Verify repaired project",
                        "action": "test",
                        "target_file": "multi_test/app.py",
                        "target_files": [
                            "multi_test/app.py",
                            "multi_test/config.py",
                        ],
                    },
                    {
                        "title": "Review repair result",
                        "action": "review",
                    },
                ]

            else:
                steps = [
                    {
                        "title": f"Understand the goal: {goal}",
                        "action": "design",
                    },
                    {
                        "title": "Work through implementation",
                        "action": "implement",
                        "target_file": "",
                        "target_files": [],
                        "target_function": "",
                        "mutation_mode": "file",
                        "next_action": "generate_file_replacement",
                        "mutation_ready": True,
                        "payload_required": True,
                    },
                    {
                        "title": "Review result",
                        "action": "review",
                    },
                ]

            project_context = build_project_brain_context()

            brain_context = {
                "project_name": project_context.project_name,
                "active_checkpoint": project_context.active_checkpoint,
                "blocker": project_context.blocker,
                "next_move": project_context.next_move,
            }

            print(
                "DEBUG AUTOPLAN STEPS BEFORE START:",
                steps,
            )

            for step in steps:
                if step.get("action") == "implement":
                    step.setdefault(
                        "target_file",
                        "",
                    )

                    step.setdefault(
                        "target_function",
                        "",
                    )

                    step["mutation_mode"] = "file"

                    step.setdefault(
                        "next_action",
                        "generate_file_replacement",
                    )

                    step["mutation_ready"] = True
                    step["payload_required"] = True
            print(
                "AUTOPLAN BEFORE START",
                {

                    "has_chat_execution_service": hasattr(
                        self,
                        "chat_execution_service",
                    ),
                    "has_chat_service": hasattr(
                        self,
                        "chat_service",
                    ),
                    "session_id": session_id,
                    "goal": goal,
                    "steps": len(steps),
                },
                flush=True,
            )

            print(
                "DEBUG STEPS RIGHT BEFORE START =",
                steps,
                flush=True,
            )

            state = self.chat_execution_service.start(
                session_id=session_id,
                goal=goal,
                steps=steps,
                context={
                    "source": "auto_plan",
                    "task_goal": goal,
                    "step_count": len(steps),
                    "steps": steps,
                    "project": "Nova",
                    "execution_reason": (
                        "Complete the user's requested task "
                        "through a guided execution workflow."
                    ),
                    "project_brain": brain_context,
                },
            )

            if state:
                if self.chat_service and hasattr(
                    self.chat_service,
                    "_save_execution_state",
                ):
                    self.chat_service._save_execution_state(
                        session_id,
                        state,
                    )

            step_lines = []

            for index, step in enumerate(steps):
                if isinstance(step, dict):
                    step_lines.append(
                        f"{index + 1}. {step.get('title', 'Execution step')}"
                    )
                else:
                    step_lines.append(
                        f"{index + 1}. {step}"
                    )

            reply_text = (
                "Mission created.\n\n"
                f"Goal: {goal}\n\n"
                "Steps:\n"
                + "\n".join(step_lines)
                + "\n\n"
                "Send `next` to run the first step."
            )

            return {
                "ok": True,
                "skip_cleanup": True,
                "skip_post_processing": True,
                "skip_rewrite": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply_text,
                    "content": reply_text,
                    "execution_state": state,
                },
                "execution_state": state,
            }

        except Exception as exc:
            self.logger.exception(
                "[NovaExecutionAutoPlanStart] failed"
            )

            reply_text = (
                "Execution auto-plan start failed: "
                + str(exc)
            )

            return {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply_text,
                    "content": reply_text,
                },
            }

    def try_execution_status(
        self,
        session_id,
        user_text,
    ):
        try:
            clean = (
                " ".join(
                    str(user_text or "")
                    .strip()
                    .lower()
                    .split()
                )
                .rstrip("?!.")
            )

            status_questions = {
                "status",
                "execution status",
                "mission status",
                "what comes next",
            }

            if clean not in status_questions:
                return None

            state = self.chat_execution_service.get_state(
                session_id
            )

            if (
                not isinstance(state, dict)
                or state.get("status") == "idle"
            ):
                return None

            goal = str(
                state.get("goal")
                or "Untitled mission"
            )

            status = str(
                state.get("status")
                or "ready"
            )

            task_type = str(
                state.get("task_type")
                or "general"
            )

            project_brain = (
                state.get("context", {})
                .get("project_brain", {})
                if isinstance(state, dict)
                else {}
            )

            next_action = state.get(
                "next_action",
                {},
            )

            reply_text = (
                f"Active mission: {goal}\n"
                f"Type: {task_type}\n"
                f"Status: {status}\n"
                f"Checkpoint: {project_brain.get('active_checkpoint', 'Not available')}\n"
                f"Blocker: {project_brain.get('blocker', 'None')}\n"
                f"Next move: {project_brain.get('next_move') or 'No next move available'}\n"
                f"Next action: {next_action.get('step') or 'Waiting for instruction'}\n"
            )

            return {
                "ok": True,
                "text": reply_text,
                "content": reply_text,
                "skip_cleanup": True,
                "skip_post_processing": True,
                "skip_rewrite": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply_text,
                    "content": reply_text,
                    "execution_state": state,
                },
                "execution_state": state,
            }

        except Exception:
            return None