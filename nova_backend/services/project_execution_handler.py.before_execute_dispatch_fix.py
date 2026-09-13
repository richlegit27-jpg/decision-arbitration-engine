from __future__ import annotations

from typing import Any, Dict

from nova_backend.services.execution_handler import (
    NextMove,
)


class ProjectExecutionHandler:
    """
    Bridge between ChatExecutionService and Nova's existing
    function-based execution system.

    Project tasks are translated into NextMove objects and sent to
    the existing default_executor when execution is possible.
    """

    def _make_move(
        self,
        current_step: Dict[str, Any],
    ) -> NextMove | None:

        step_action = str(
            current_step.get("action") or "analysis"
        ).strip().lower()

        step_id = str(
            current_step.get("id") or ""
        ).strip()

        if step_action in {
            "analysis",
            "analyze",
            "research",
            "review",
            "verify",
            "verification",
            "validate",
            "validation",
            "plan",
            "planning",
            "design",
            "architecture",
            "architect",
            "document",
            "documentation",
            "specify",
            "specification",
        }:

            return NextMove(
                id=step_id or "project-analysis",
                type="log",
                payload={
                    "message": str(
                        current_step.get("description")
                        or current_step.get("title")
                        or "Project analysis completed."
                    )
                },
            )

        if step_action == "create":
            target_files = (
                current_step.get("target_files")
                or []
            )

            if isinstance(target_files, str):
                target_files = [target_files]

            target_file = str(
                current_step.get("target_file") or ""
            ).strip()

            if not target_files and target_file:
                target_files = [target_file]

            code = str(
                current_step.get("content")
                or current_step.get("code")
                or ""
            )

            if target_files and code.strip():
                return NextMove(
                    id=step_id or "project-create",
                    type="fix_file",
                    payload={
                        "file_paths": target_files,
                        "file_path": target_files[0],
                        "code": code,
                    },
                )

            return NextMove(
                id=step_id or "project-create-log",
                type="log",
                payload={
                    "message": str(
                        current_step.get("description")
                        or current_step.get("title")
                        or "Project creation step completed."
                    )
                },
            )


        if step_action in {
            "build",
            "implement",
            "edit",
            "write",
            "modify",
        }:
            target_files = (
                current_step.get("target_files")
                or []
            )

            if isinstance(target_files, str):
                target_files = [
                    target_files
                ]

            target_file = str(
                current_step.get("target_file") or ""
            ).strip()

            if not target_files and target_file:
                target_files = [
                    target_file
                ]

            code = str(
                current_step.get("content")
                or current_step.get("code")
                or ""
            )

            if not target_files or not code.strip():
                return None

            return NextMove(
                id=step_id or "project-fix-file",
                type="fix_file",
                payload={
                    "file_paths": target_files,
                    "file_path": (
                        target_files[0]
                        if target_files
                        else ""
                    ),
                    "code": code,
                },
            )

        if step_action == "patch":
            target_files = (
                current_step.get("target_files")
                or []
            )

            if isinstance(target_files, str):
                target_files = [
                    target_files
                ]

            target_file = str(
                current_step.get("target_file") or ""
            ).strip()

            if not target_files and target_file:
                target_files = [
                    target_file
                ]

            function_name = str(
                current_step.get("target_function") or ""
            ).strip()

            replacement = str(
                current_step.get("replacement")
                or current_step.get("content")
                or current_step.get("code")
                or ""
            )

            if (
                target_files
                and function_name
                and replacement.strip()
            ):
                return NextMove(
                    id=step_id or "project-function-fix",
                    type="apply_function_fix",
                    payload={
                        "file_paths": target_files,
                        "file_path": (
                            target_files[0]
                            if target_files
                            else ""
                        ),
                        "function_name": function_name,
                        "replacement": replacement,
                    },
                )

            if target_files and replacement.strip():
                return NextMove(
                    id=step_id or "project-fix-file",
                    type="fix_file",
                    payload={
                        "file_paths": target_files,
                        "file_path": (
                            target_files[0]
                            if target_files
                            else ""
                        ),
                        "code": replacement,
                    },
                )

            return None

        if step_action in {
            "command",
            "shell",
            "run_command",
        }:
            command = str(
                current_step.get("command") or ""
            ).strip()

            if not command:
                return None

            return NextMove(
                id=step_id or "project-command",
                type="run_step",
                payload={
                    "command": command,
                    "step": current_step,
                },
            )

        return None

    def __init__(
        self,
        default_executor=None,
        execution_step_service=None,
    ):
        self.default_executor = default_executor
        self.execution_step_service = execution_step_service



    def _validate_completion(
        self,
        session_id: str,
        current_step: Dict[str, Any],
        result: str,
    ) -> bool:
        """
        Validate an execution result against the step's declared
        completion criteria and expected output.

        Returns True when no criteria are declared or the validator
        returns PASS. Returns False when the result does not satisfy
        the declared completion requirements.
        """

        completion_criteria = current_step.get(
            "completion_criteria"
        ) or []

        expected_output = str(
            current_step.get("expected_output")
            or ""
        ).strip()

        if isinstance(completion_criteria, str):
            completion_criteria = [
                completion_criteria
            ]

        completion_criteria = [
            str(item).strip()
            for item in completion_criteria
            if str(item).strip()
        ]

        if not completion_criteria and not expected_output:
            return True

        validation_prompt = (
            "Evaluate whether the execution result satisfies "
            "the required completion conditions.\n\n"
            f"Execution result:\n{result}\n\n"
            f"Completion criteria:\n"
            f"{completion_criteria}\n\n"
            f"Expected output:\n{expected_output}\n\n"
            "Return only one word: PASS or FAIL."
        )

        validation_result = (
            self.execution_step_service.execute_step_logic(
                session_id=session_id,
                step={
                    "id": (
                        f"{current_step.get('id', 'project-step')}"
                        "-completion-validation"
                    ),
                    "title": "Validate completion",
                    "description": validation_prompt,
                    "type": "analysis",
                    "status": "pending",
                },
            )
        )

        if isinstance(validation_result, dict):
            validation_text = str(
                validation_result.get("result")
                or validation_result.get("output")
                or ""
            ).strip().upper()
        else:
            validation_text = str(
                validation_result
                or ""
            ).strip().upper()

        return validation_text.startswith("PASS")

    def _normalize_step_action(
        self,
        action,
    ):
        normalized = str(
            action or "analysis"
        ).strip().lower()

        if not normalized:
            return "analysis"

        action_aliases = {
            "create": {
                "create",
                "create artifact",
                "create a small test artifact",
                "create the second phase artifact",
                "generate",
                "generate artifact",
                "make",
                "produce",
            },
            "validate": {
                "validate",
                "validate artifact",
                "validate the test artifact",
                "validate the second phase artifact",
                "verify",
                "check",
                "test",
                "verification",
            },
            "analysis": {
                "analysis",
                "analyze",
                "inspect",
                "research",
                "review",
                "plan",
                "planning",
                "design",
                "architecture",
                "architect",
                "document",
                "documentation",
                "specify",
                "specification",
            },
            "build": {
                "build",
                "implement",
                "implementation",
                "edit",
                "write",
                "modify",
                "patch",
                "fix",
            },
            "command": {
                "command",
                "shell",
                "run command",
                "run_command",
            },
        }

        for canonical_action, aliases in action_aliases.items():
            if normalized in aliases:
                return canonical_action

        if normalized.startswith("create "):
            return "create"

        if normalized.startswith("generate "):
            return "create"

        if normalized.startswith("make "):
            return "create"

        if normalized.startswith("produce "):
            return "create"

        if normalized.startswith("validate "):
            return "validate"

        if normalized.startswith("verify "):
            return "validate"

        if normalized.startswith("check "):
            return "validate"

        if normalized.startswith("test "):
            return "validate"

        if normalized.startswith("build "):
            return "build"

        if normalized.startswith("implement "):
            return "build"

        if normalized.startswith("write "):
            return "build"

        if normalized.startswith("modify "):
            return "build"

        if normalized.startswith("patch "):
            return "build"

        if normalized.startswith("fix "):
            return "build"

        if normalized.startswith("run "):
            return "command"

        return normalized

    def _advance_after_success(
        self,
        state: Dict[str, Any],
        steps,
        current_index: int,
        current_step: Dict[str, Any],
    ) -> Dict[str, Any]:
        current_step["status"] = "completed"

        steps[current_index] = current_step

        history = list(
            state.get("history") or []
        )

        history.append(
            {
                "step_id": current_step.get("id"),
                "task_id": current_step.get(
                    "task_id"
                ),
                "status": "completed",
                "action": current_step.get(
                    "action"
                ),
                "result": current_step.get(
                    "result"
                ),
            }
        )

        state["history"] = history

        completed_ids = set()
        completed_titles = set()

        for step in steps:
            if not isinstance(step, dict):
                continue

            status = str(
                step.get("status") or ""
            ).strip().lower()

            if status not in {
                "completed",
                "complete",
                "done",
                "success",
            }:
                continue

            for key in (
                "id",
                "task_id",
            ):
                value = str(
                    step.get(key) or ""
                ).strip()

                if value:
                    completed_ids.add(value)

            title = str(
                step.get("title") or ""
            ).strip().lower()

            if title:
                completed_titles.add(title)

        def dependency_variants(value):
            text = str(value or "").strip().lower()

            if not text:
                return set()

            variants = {
                text,
            }

            prefixes = (
                "project_task_project_task_",
                "project_task_",
                "task_",
                "step_",
            )

            changed = True

            while changed:
                changed = False

                for variant in list(variants):
                    for prefix in prefixes:
                        if variant.startswith(prefix):
                            stripped = variant[len(prefix):].strip()

                            if stripped and stripped not in variants:
                                variants.add(stripped)
                                changed = True

            return variants

        completed_id_variants = set()

        for completed_id in completed_ids:
            completed_id_variants.update(
                dependency_variants(completed_id)
            )

        completed_title_variants = {
            str(title or "").strip().lower()
            for title in completed_titles
            if str(title or "").strip()
        }

        def dependency_is_satisfied(dependency):
            dependency_text = str(
                dependency or ""
            ).strip()

            if not dependency_text:
                return True

            dependency_lower = dependency_text.lower()

            if dependency_lower in completed_title_variants:
                return True

            dependency_variants_set = dependency_variants(
                dependency_text
            )

            if (
                dependency_variants_set
                & completed_id_variants
            ):
                return True

            for completed_id in completed_ids:
                completed_lower = str(
                    completed_id or ""
                ).strip().lower()

                if not completed_lower:
                    continue

                if completed_lower.endswith(
                    "-" + dependency_lower
                ):
                    return True

                if dependency_lower.endswith(
                    "-" + completed_lower
                ):
                    return True

            return False

        next_index = current_index + 1
        next_runnable_index = None
        blocked_indexes = []

        while next_index < len(steps):
            candidate = steps[next_index]

            if not isinstance(candidate, dict):
                blocked_indexes.append(next_index)
                next_index += 1
                continue

            candidate_status = str(
                candidate.get("status") or ""
            ).strip().lower()

            if candidate_status in {
                "completed",
                "complete",
                "done",
                "success",
            }:
                next_index += 1
                continue

            dependencies = (
                candidate.get("dependencies")
                or candidate.get("depends_on")
                or candidate.get("dependency_ids")
                or []
            )

            if isinstance(dependencies, str):
                dependencies = [
                    dependencies
                ]

            unresolved_dependencies = [
                dependency
                for dependency in dependencies
                if not dependency_is_satisfied(
                    dependency
                )
            ]

            if unresolved_dependencies:
                candidate["status"] = "blocked"
                candidate["blocked"] = True
                candidate["waiting"] = True
                candidate["unresolved_dependencies"] = (
                    unresolved_dependencies
                )

                steps[next_index] = candidate
                blocked_indexes.append(next_index)

                print(
                    "[PROJECT DEPENDENCY BLOCKED]",
                    {
                        "step_id": candidate.get("id"),
                        "title": candidate.get("title"),
                        "unresolved_dependencies": (
                            unresolved_dependencies
                        ),
                    },
                    flush=True,
                )

                next_index += 1
                continue

            next_runnable_index = next_index
            break

        state["steps"] = steps

        if next_runnable_index is None:
            incomplete_steps = []

            for index, step in enumerate(steps):
                if not isinstance(step, dict):
                    continue

                status = str(
                    step.get("status") or ""
                ).strip().lower()

                if status not in {
                    "completed",
                    "complete",
                    "done",
                    "success",
                }:
                    incomplete_steps.append(
                        {
                            "index": index,
                            "id": step.get("id"),
                            "title": step.get("title"),
                            "status": step.get("status"),
                            "dependencies": (
                                step.get("dependencies")
                                or step.get("depends_on")
                                or []
                            ),
                        }
                    )

            state["current_index"] = len(steps)
            state["current_step"] = None
            state["waiting"] = bool(
                incomplete_steps
            )
            state["complete"] = not bool(
                incomplete_steps
            )
            state["status"] = (
                "waiting"
                if incomplete_steps
                else "complete"
            )

            if incomplete_steps:
                state["error"] = (
                    "Execution is waiting for unresolved "
                    "task dependencies."
                )
            else:
                state.pop("error", None)

            return state

        next_step = steps[next_runnable_index]

        if isinstance(next_step, dict):
            next_step["status"] = "active"
            next_step["blocked"] = False
            next_step["waiting"] = False
            next_step.pop(
                "unresolved_dependencies",
                None,
            )
            steps[next_runnable_index] = next_step

        state["steps"] = steps
        state["current_index"] = next_runnable_index
        state["status"] = "running"
        state["complete"] = False
        state["waiting"] = False
        state["current_step"] = next_step

        return state
    def run_next_move(
        self,
        action: str,
        session_id: str,
        execution_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self.run_next_step(
            action=action,
            session_id=session_id,
            execution_state=execution_state,
        )

    def run_next_step(
        self,
        action: str,
        session_id: str,
        execution_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        state = (
            dict(execution_state)
            if isinstance(execution_state, dict)
            else {}
        )

        steps = state.get("steps") or []

        current_index = int(
            state.get("current_index") or 0
        )

        if current_index >= len(steps):
            dependency_waiting = bool(
                state.get("waiting")
            ) or any(
                isinstance(step, dict)
                and (
                    str(
                        step.get("status") or ""
                    ).strip().lower()
                    in {
                        "blocked",
                        "waiting",
                    }
                    or bool(
                        step.get("blocked")
                    )
                    or bool(
                        step.get("waiting")
                    )
                    or bool(
                        step.get(
                            "unresolved_dependencies"
                        )
                    )
                )
                for step in steps
            )

            if dependency_waiting:
                state["status"] = "waiting"
                state["waiting"] = True
                state["complete"] = False
                state["current_step"] = None
                state["error"] = (
                    state.get("error")
                    or
                    "Execution is waiting for unresolved task dependencies."
                )
            else:
                state["status"] = "complete"
                state["complete"] = True
                state["waiting"] = False
                state["current_step"] = None
                state.pop("error", None)

            return {
                "ok": True,
                "execution_state": state,
            }

        current_step = steps[current_index]

        if not isinstance(current_step, dict):
            state["status"] = "failed"
            state["complete"] = False
            state["waiting"] = False
            state["error"] = (
                "Current execution step is invalid."
            )

            return {
                "ok": False,
                "error": state["error"],
                "execution_state": state,
            }

        current_step = dict(current_step)

        current_step["status"] = "active"

        step_action = self._normalize_step_action(
            current_step.get("action")
        )

        print(
            "LIVE STEP ACTION DISPATCH",
            {
                "incoming_action": repr(action),
                "normalized_step_action": repr(step_action),
                "current_step_id": current_step.get("id"),
                "current_step_title": current_step.get("title"),
                "current_step_action": repr(current_step.get("action")),
                "step_keys": list(current_step.keys()),
                "analysis_match": step_action in {
                    "analysis",
                    "analyze",
                    "inspect",
                    "research",
                    "review",
                    "plan",
                    "planning",
                    "design",
                    "document",
                    "documentation",
                },
            },
            flush=True,
        )

        title = str(
            current_step.get("title")
            or "Project task"
        ).strip()

        description = str(
            current_step.get("description") or ""
        ).strip()

        context = dict(
            state.get("context") or {}
        )

        context["project_execution"] = True
        context["execution_action"] = action
        context["current_task"] = {
            "id": current_step.get("id"),
            "task_id": current_step.get(
                "task_id"
            ),
            "title": title,
            "description": description,
            "action": step_action,
            "target_file": current_step.get(
                "target_file"
            ),
            "target_files": current_step.get(
                "target_files"
            ),
            "target_function": current_step.get(
                "target_function"
            ),
            "command": current_step.get(
                "command"
            ),
        }

        state["context"] = context
        state["current_step"] = current_step
        state["steps"] = steps

        print(
            "PROJECT EXECUTION HANDLER STEP",
            {
                "session_id": session_id,
                "action": action,
                "step_action": step_action,
                "step_id": current_step.get("id"),
                "title": title,
            },
            flush=True,
        )

        # ---------------------------------------------------------
        # ANALYSIS / REVIEW / PLANNING
        # ---------------------------------------------------------

        if step_action in {
            "analysis",
            "analyze",
            "inspect",
            "research",
            "review",
            "plan",
            "planning",
            "design",
            "document",
            "documentation",
        }:

            if self.execution_step_service is None:
                current_step["status"] = "failed"
                current_step["error"] = (
                    "ExecutionStepService is unavailable for "
                    "AI execution."
                )

                steps[current_index] = current_step
                state["steps"] = steps
                state["status"] = "failed"
                state["waiting"] = False
                state["complete"] = False
                state["error"] = current_step["error"]
                state["current_step"] = current_step

                return {
                    "ok": False,
                    "error": current_step["error"],
                    "execution_state": state,
                }

            try:
                generated_step = (
                    self.execution_step_service.execute_step_logic(
                        session_id=session_id,
                        step=current_step,
                    )
                )

                if isinstance(generated_step, dict):
                    current_step = generated_step

                steps[current_index] = current_step
                state["steps"] = steps
                state["current_step"] = current_step
                state["waiting"] = False

                step_status = str(
                    current_step.get("status") or ""
                ).strip().lower()

                result = str(
                    current_step.get("result") or ""
                ).strip()

                completion_status = str(
                    current_step.get("completion_status")
                    or current_step.get("execution_status")
                    or ""
                ).strip().lower()

                # Explicit failure returned by the AI service.
                if step_status in {
                    "failed",
                    "error",
                }:
                    raise RuntimeError(
                        current_step.get("error")
                        or "AI execution step failed."
                    )

                if completion_status in {
                    "failed",
                    "error",
                    "incomplete",
                }:
                    raise RuntimeError(
                        current_step.get("error")
                        or (
                            "AI execution step did not complete. "
                            f"Completion status: {completion_status}"
                        )
                    )

                # Explicit waiting state must not advance the project.
                if step_status in {
                    "waiting",
                    "waiting_approval",
                    "needs_input",
                } or completion_status in {
                    "waiting",
                    "waiting_approval",
                }:
                    current_step["status"] = "waiting"
                    state["steps"] = steps
                    state["current_step"] = current_step
                    state["status"] = "waiting"
                    state["waiting"] = True
                    state["complete"] = False

                    return {
                        "ok": True,
                        "execution_state": state,
                        "result": result,
                    }

                # An AI step cannot complete without a usable result.
                if not result:
                    raise RuntimeError(
                        "AI execution returned an empty result."
                    )

                if not self._validate_completion(
                    session_id=session_id,
                    current_step=current_step,
                    result=result,
                ):
                    current_step["status"] = "waiting"
                    current_step["completion_status"] = "needs_input"
                    current_step["next_action"] = (
                        "Satisfy the completion criteria and retry."
                    )
                    current_step["mutation_ready"] = False
                    current_step["payload_required"] = False
                    current_step["mutation_mode"] = None
                    current_step["error"] = None

                    steps[current_index] = current_step
                    state["steps"] = steps
                    state["current_step"] = current_step
                    state["waiting"] = True
                    state["complete"] = False
                    state["status"] = "waiting"

                    return {
                        "ok": True,
                        "execution_state": state,
                        "result": result,
                        "completion_validated": False,
                    }

                current_step["result"] = result
                current_step["status"] = "completed"
                current_step["completion_status"] = "completed"
                current_step["next_action"] = None
                current_step["mutation_ready"] = False
                current_step["error"] = None

                steps[current_index] = current_step
                state["steps"] = steps
                state["current_step"] = current_step

                return {
                    "ok": True,
                    "execution_state": (
                        self._advance_after_success(
                            state=state,
                            steps=steps,
                            current_index=current_index,
                            current_step=current_step,
                        )
                    ),
                    "result": result,
                    "completion_validated": True,
                }

            except Exception as exc:
                current_step["status"] = "failed"
                current_step["error"] = (
                    f"AI execution failed: {exc}"
                )

                steps[current_index] = current_step
                state["steps"] = steps
                state["status"] = "failed"
                state["waiting"] = False
                state["complete"] = False
                state["error"] = current_step["error"]
                state["current_step"] = current_step

                return {
                    "ok": False,
                    "error": current_step["error"],
                    "execution_state": state,
                }

        # ---------------------------------------------------------
        # TEST / VERIFICATION EXECUTION
        # ---------------------------------------------------------

        if step_action in {
            "test",
            "verify",
            "verification",
            "validate",
            "validation",
            "check",
        }:

            if self.execution_step_service is None:

                current_step["status"] = "failed"

                current_step["error"] = (
                    "ExecutionStepService is unavailable for "
                    "test execution."
                )

                steps[current_index] = current_step

                state["steps"] = steps
                state["status"] = "failed"
                state["waiting"] = False
                state["complete"] = False
                state["error"] = current_step["error"]
                state["current_step"] = current_step

                return {
                    "ok": False,
                    "error": current_step["error"],
                    "execution_state": state,
                }

            try:

                generated_step = (
                    self.execution_step_service.execute_step_logic(
                        session_id=session_id,
                        step=current_step,
                    )
                )

                if isinstance(
                    generated_step,
                    dict,
                ):
                    current_step = generated_step

                result = str(
                    current_step.get(
                        "result",
                        "",
                    )
                    or ""
                ).strip()

                if not result:
                    raise RuntimeError(
                        "AI execution returned an empty result."
                    )

                if not self._validate_completion(
                    session_id=session_id,
                    current_step=current_step,
                    result=result,
                ):
                    current_step["status"] = "running"
                    current_step["completion_status"] = "incomplete"
                    current_step["next_action"] = (
                        "Satisfy the completion criteria and retry."
                    )
                    current_step["mutation_ready"] = False
                    current_step["payload_required"] = False
                    current_step["mutation_mode"] = None
                    current_step["error"] = None

                    steps[current_index] = current_step
                    state["steps"] = steps
                    state["current_step"] = current_step
                    state["waiting"] = False
                    state["complete"] = False
                    state["status"] = "running"

                    return {
                        "ok": True,
                        "execution_state": state,
                        "result": result,
                        "completion_validated": False,
                    }

                current_step["result"] = result
                current_step["status"] = "completed"
                current_step["next_action"] = None
                current_step["mutation_ready"] = False
                current_step["payload_required"] = False
                current_step["mutation_mode"] = None
                current_step["error"] = None

                steps[current_index] = current_step

                state["steps"] = steps
                state["current_step"] = current_step

                return {
                    "ok": True,
                    "execution_state": (
                        self._advance_after_success(
                            state=state,
                            steps=steps,
                            current_index=current_index,
                            current_step=current_step,
                        )
                    ),
                    "result": result,
                }

            except Exception as exc:

                current_step["status"] = "failed"

                current_step["error"] = (
                    f"Test execution failed: {exc}"
                )

                steps[current_index] = current_step

                state["steps"] = steps
                state["status"] = "failed"
                state["waiting"] = False
                state["complete"] = False
                state["error"] = current_step["error"]
                state["current_step"] = current_step

                return {
                    "ok": False,
                    "error": current_step["error"],
                    "execution_state": state,
                }

        # ---------------------------------------------------------
        # BUILD EXECUTION MOVE
        # ---------------------------------------------------------

        move = self._make_move(
            current_step
        )

        # ---------------------------------------------------------
        # LOCAL LOG MOVE
        # ---------------------------------------------------------

        if move is not None and move.type == "log":
            current_step["result"] = str(
                move.payload.get("message")
                or f"{title} completed."
            )

            state = self._advance_after_success(
                state=state,
                steps=steps,
                current_index=current_index,
                current_step=current_step,
            )

            return {
                "ok": True,
                "execution_state": state,
                "result": current_step["result"],
            }

        # ---------------------------------------------------------
        # MISSING IMPLEMENT TARGET
        # ---------------------------------------------------------

        if move is None and step_action in {
            "build",
            "implement",
            "implementation",
            "create",
            "edit",
            "write",
            "modify",
            "patch",
            "fix",
        }:

            target_file = str(
                current_step.get("target_file") or ""
            ).strip()

            target_files = (
                current_step.get("target_files")
                or []
            )

            if (
                not target_file
                and not target_files
            ):
                current_step["next_action"] = (
                    "execute_general_task"
                )

                current_step["mutation_ready"] = True

                if self.execution_step_service is None:
                    current_step["status"] = "failed"

                    current_step["error"] = (
                        "ExecutionStepService is unavailable for "
                        "general task execution."
                    )

                    steps[current_index] = current_step

                    state["steps"] = steps
                    state["status"] = "failed"
                    state["waiting"] = False
                    state["complete"] = False
                    state["error"] = current_step["error"]
                    state["current_step"] = current_step

                    return {
                        "ok": False,
                        "error": current_step["error"],
                        "execution_state": state,
                    }

                try:
                    generated_step = (
                        self.execution_step_service.execute_step_logic(
                            session_id=session_id,
                            step=current_step,
                        )
                    )

                    if isinstance(generated_step, dict):
                        current_step = generated_step

                    steps[current_index] = current_step

                    state["steps"] = steps
                    state["current_step"] = current_step
                    state["waiting"] = False

                    step_status = str(
                        current_step.get("status") or ""
                    ).strip().lower()

                    if step_status in {
                        "failed",
                        "error",
                    }:
                        state["status"] = "failed"
                        state["complete"] = False
                        state["error"] = (
                            current_step.get("error")
                            or "Project execution step failed."
                        )

                        return {
                            "ok": False,
                            "error": state["error"],
                            "execution_state": state,
                        }

                    if step_status in {
                        "waiting",
                        "waiting_approval",
                    }:
                        state["status"] = "waiting"
                        state["waiting"] = True
                        state["complete"] = False

                        return {
                            "ok": True,
                            "execution_state": state,
                        }

                    current_step["status"] = "completed"

                    state = self._advance_after_success(
                        state=state,
                        steps=steps,
                        current_index=current_index,
                        current_step=current_step,
                    )

                    return {
                        "ok": True,
                        "execution_state": state,
                        "result": current_step.get("result"),
                    }

                except Exception as exc:
                    current_step["status"] = "failed"

                    current_step["error"] = (
                        f"Project general task execution failed: {exc}"
                    )

                    steps[current_index] = current_step

                    state["steps"] = steps
                    state["status"] = "failed"
                    state["waiting"] = False
                    state["complete"] = False
                    state["error"] = current_step["error"]
                    state["current_step"] = current_step

                    return {
                        "ok": False,
                        "error": current_step["error"],
                        "execution_state": state,
                    }

            content = str(
                current_step.get("content")
                or current_step.get("code")
                or current_step.get("replacement")
                or ""
            )

            if not content.strip():
                if self.execution_step_service is None:
                    current_step["status"] = "failed"

                    current_step["error"] = (
                        "ExecutionStepService is unavailable for "
                        "file replacement generation."
                    )

                    steps[current_index] = current_step

                    state["steps"] = steps
                    state["status"] = "failed"
                    state["waiting"] = False
                    state["complete"] = False
                    state["error"] = current_step["error"]
                    state["current_step"] = current_step

                    return {
                        "ok": False,
                        "error": current_step["error"],
                        "execution_state": state,
                    }

                current_step["next_action"] = (
                    "generate_file_replacement"
                )

                current_step["mutation_ready"] = True

                try:
                    generated_step = (
                        self.execution_step_service.execute_step_logic(
                            session_id=session_id,
                            step=current_step,
                        )
                    )

                    if isinstance(generated_step, dict):
                        current_step = generated_step

                    steps[current_index] = current_step

                    state["steps"] = steps
                    state["current_step"] = current_step
                    state["waiting"] = False

                    step_status = str(
                        current_step.get("status") or ""
                    ).strip().lower()

                    if step_status in {
                        "failed",
                        "error",
                    }:
                        state["status"] = "failed"
                        state["complete"] = False
                        state["error"] = (
                            current_step.get("error")
                            or "Project execution step failed."
                        )

                        return {
                            "ok": False,
                            "error": state["error"],
                            "execution_state": state,
                        }

                    if step_status in {
                        "waiting",
                        "waiting_approval",
                    }:
                        state["status"] = "waiting"
                        state["waiting"] = True
                        state["complete"] = False

                        return {
                            "ok": True,
                            "execution_state": state,
                        }

                    current_step["status"] = (
                        "completed"
                        if step_status not in {
                            "completed",
                            "complete",
                        }
                        else current_step["status"]
                    )

                    current_step["completion_status"] = "completed"
                    current_step["next_action"] = None
                    current_step["mutation_ready"] = False
                    current_step["payload_required"] = False
                    current_step["mutation_mode"] = None
                    current_step["error"] = None

                    steps[current_index] = current_step

                    state["steps"] = steps
                    state["current_step"] = current_step

                    state = self._advance_after_success(
                        state=state,
                        steps=steps,
                        current_index=current_index,
                        current_step=current_step,
                    )

                    return {
                        "ok": True,
                        "execution_state": state,
                        "result": current_step.get("result"),
                    }

                except Exception as exc:
                    current_step["status"] = "failed"

                    current_step["error"] = (
                        f"Project file generation failed: {exc}"
                    )

                    steps[current_index] = current_step

                    state["steps"] = steps
                    state["status"] = "failed"
                    state["waiting"] = False
                    state["complete"] = False
                    state["error"] = current_step["error"]
                    state["current_step"] = current_step

                    return {
                        "ok": False,
                        "error": current_step["error"],
                        "execution_state": state,
                    }

                content = str(
                    current_step.get("content")
                    or current_step.get("code")
                    or current_step.get("replacement")
                    or ""
                )

                if not content.strip():
                    current_step["status"] = "failed"

                    current_step["error"] = (
                        "File generation completed without usable content."
                    )

                    steps[current_index] = current_step

                    state["steps"] = steps
                    state["status"] = "failed"
                    state["waiting"] = False
                    state["complete"] = False
                    state["error"] = current_step["error"]
                    state["current_step"] = current_step

                    return {
                        "ok": False,
                        "error": current_step["error"],
                        "execution_state": state,
                    }

        # ---------------------------------------------------------
        # EXECUTE TASK
        # ---------------------------------------------------------

        if move is None and step_action in {
            "execute",
            "run",
            "run_file",
            "run_script",
        }:
            execution_file = str(
                current_step.get("execution_file")
                or current_step.get("target_file")
                or ""
            ).strip()

            command = str(
                current_step.get("command")
                or ""
            ).strip()

            if not execution_file and not command:
                current_step["status"] = "failed"

                current_step["error"] = (
                    "Execute task has no execution_file or command."
                )

                steps[current_index] = current_step

                state["steps"] = steps
                state["status"] = "failed"
                state["waiting"] = False
                state["complete"] = False
                state["error"] = current_step["error"]
                state["current_step"] = current_step

                return {
                    "ok": False,
                    "error": current_step["error"],
                    "execution_state": state,
                }

            execute_payload = dict(current_step)

            if execution_file:
                execute_payload["execution_file"] = (
                    execution_file
                )

            if command:
                execute_payload["command"] = command

            move = self._make_move(
                execute_payload
            )

            if move is None:
                current_step["status"] = "failed"

                current_step["error"] = (
                    "Execute task could not be converted "
                    "into an execution move."
                )

                steps[current_index] = current_step

                state["steps"] = steps
                state["status"] = "failed"
                state["waiting"] = False
                state["complete"] = False
                state["error"] = current_step["error"]
                state["current_step"] = current_step

                return {
                    "ok": False,
                    "error": current_step["error"],
                    "execution_state": state,
                }

            # ---------------------------------------------------------
            # NO EXECUTOR
            # ---------------------------------------------------------

            if not callable(self.default_executor):
                current_step["status"] = "waiting"

                current_step["result"] = (
                    "Project execution is waiting because "
                    "the default executor is unavailable."
                )

                steps[current_index] = current_step

                state["steps"] = steps
                state["status"] = "waiting"
                state["waiting"] = True
                state["complete"] = False
                state["current_step"] = current_step

                return {
                    "ok": True,
                    "execution_state": state,
                }

        # ---------------------------------------------------------
        # EXECUTE REAL MOVE
        # ---------------------------------------------------------

        if move is not None:
            print(
                "PROJECT EXECUTION HANDLER CALLING EXECUTOR",
                {
                    "move_type": move.type,
                    "move_id": move.id,
                    "payload": move.payload,
                },
                flush=True,
            )

            try:

                if (
                    move.type == "run_step"
                    and isinstance(
                        move.payload,
                        dict,
                    )
                    and isinstance(
                        move.payload.get("step"),
                        dict,
                    )
                    and str(
                        move.payload["step"].get(
                            "action",
                            "",
                        )
                    ).strip().lower()
                    in {
                        "command",
                        "shell",
                        "run_command",
                    }
                ):

                    if self.execution_step_service is None:
                        raise RuntimeError(
                            "ExecutionStepService is unavailable "
                            "for command execution."
                        )

                    command_step = move.payload["step"]

                    execution_result = (
                        self.execution_step_service.execute_step_logic(
                            session_id=session_id,
                            step=command_step,
                        )
                    )

                    if isinstance(
                        execution_result,
                        dict,
                    ):
                        current_step.update(
                            execution_result
                        )

                    else:
                        current_step = command_step

                    steps[current_index] = current_step
                    state["steps"] = steps
                    state["current_step"] = current_step
                    state["waiting"] = False

                    result_status = str(
                        current_step.get(
                            "status",
                            "",
                        )
                        or ""
                    ).strip().lower()

                    result_output = (
                        current_step.get(
                            "result"
                        )
                    )

                    result_error = str(
                        current_step.get(
                            "error",
                            "",
                        )
                        or ""
                    ).strip()

                    print(
                        "PROJECT EXECUTION HANDLER COMMAND RESULT",
                        {
                            "status": result_status,
                            "error": result_error,
                            "result": result_output,
                        },
                        flush=True,
                    )

                    if result_status in {
                        "failed",
                        "error",
                    }:

                        current_step["status"] = "failed"

                        current_step["error"] = (
                            result_error
                            or "Command execution failed."
                        )

                        steps[current_index] = current_step

                        state["steps"] = steps
                        state["status"] = "failed"
                        state["complete"] = False
                        state["waiting"] = False
                        state["error"] = (
                            current_step["error"]
                        )
                        state["current_step"] = current_step

                        return {
                            "ok": False,
                            "error": current_step[
                                "error"
                            ],
                            "execution_state": state,
                            "result": result_output,
                        }

                    if result_status in {
                        "waiting",
                        "waiting_approval",
                    }:

                        state["status"] = "waiting"
                        state["waiting"] = True
                        state["complete"] = False

                        return {
                            "ok": True,
                            "execution_state": state,
                            "result": result_output,
                        }

                    if result_status not in {
                        "completed",
                        "complete",
                        "success",
                    }:

                        current_step["status"] = "failed"

                        current_step["error"] = (
                            result_error
                            or (
                                "Command execution returned "
                                "an invalid completion status."
                            )
                        )

                        steps[current_index] = current_step

                        state["steps"] = steps
                        state["status"] = "failed"
                        state["complete"] = False
                        state["waiting"] = False
                        state["error"] = (
                            current_step["error"]
                        )
                        state["current_step"] = current_step

                        return {
                            "ok": False,
                            "error": current_step[
                                "error"
                            ],
                            "execution_state": state,
                            "result": result_output,
                        }

                    current_step["status"] = "completed"

                    steps[current_index] = current_step

                    state = self._advance_after_success(
                        state=state,
                        steps=steps,
                        current_index=current_index,
                        current_step=current_step,
                    )

                    return {
                        "ok": True,
                        "execution_state": state,
                        "result": result_output,
                    }
                execution_result = (
                    self.default_executor(move)
                )

            except Exception as exc:
                current_step["status"] = "failed"
                current_step["error"] = str(exc)

                steps[current_index] = current_step

                state["steps"] = steps
                state["status"] = "failed"
                state["complete"] = False
                state["waiting"] = False
                state["error"] = str(exc)
                state["current_step"] = current_step

                return {
                    "ok": False,
                    "error": str(exc),
                    "execution_state": state,
                }

            result_status = str(
                getattr(
                    execution_result,
                    "status",
                    "",
                )
                or ""
            ).strip().lower()

            result_output = getattr(
                execution_result,
                "output",
                None,
            )

            result_error = str(
                getattr(
                    execution_result,
                    "error",
                    "",
                )
                or ""
            ).strip()

            print(
                "PROJECT EXECUTION HANDLER RESULT",
                {
                    "move_type": move.type,
                    "status": result_status,
                    "error": result_error,
                },
                flush=True,
            )

            if result_status in {
                "success",
                "completed",
                "complete",
            }:
                current_step["result"] = result_output

                current_step.pop(
                    "error",
                    None,
                )

                state = self._advance_after_success(
                    state=state,
                    steps=steps,
                    current_index=current_index,
                    current_step=current_step,
                )

                return {
                    "ok": True,
                    "execution_state": state,
                    "result": result_output,
                }

            current_step["status"] = "failed"

            current_step["error"] = (
                result_error
                or "Project execution failed."
            )

            current_step["result"] = result_output

            steps[current_index] = current_step

            state["steps"] = steps
            state["status"] = "failed"
            state["complete"] = False
            state["waiting"] = False
            state["error"] = current_step["error"]
            state["current_step"] = current_step

            return {
                "ok": False,
                "error": current_step["error"],
                "execution_state": state,
            }

        # ---------------------------------------------------------
        # UNSUPPORTED ACTION
        # ---------------------------------------------------------

        current_step["status"] = "failed"

        current_step["error"] = (
            f"Unsupported project execution action: "
            f"{step_action}"
        )

        steps[current_index] = current_step

        state["steps"] = steps
        state["status"] = "failed"
        state["waiting"] = False
        state["complete"] = False
        state["error"] = current_step["error"]

        return {
            "ok": False,
            "error": current_step["error"],
            "execution_state": state,
        }

















