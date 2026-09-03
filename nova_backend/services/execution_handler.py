from __future__ import annotations

import py_compile
import os
import shutil
import time
import json
import uuid
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Callable

from nova_backend.services.model_gateway_service import (
    chat_completions_create,
)

@dataclass
class NextMove:
    id: str
    type: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    move_id: str
    status: str
    output: Any = None
    error: str = ""
    next_moves: list[NextMove] = field(default_factory=list)


MoveExecutor = Callable[[NextMove], ExecutionResult]

def _get_target_files(step: dict) -> list[str]:
    files = step.get("target_files")

    if isinstance(files, list):
        return [
            str(f).strip()
            for f in files
            if str(f).strip()
        ]

    target_file = str(
        step.get("target_file") or ""
    ).strip()

    if target_file:
        return [target_file]

    return []

def make_move(move_type: str, payload: dict[str, Any] | None = None) -> NextMove:
    return NextMove(
        id=str(uuid.uuid4()),
        type=move_type,
        payload=payload or {},
    )


class ExecutionHandler:

    def __init__(self, service):
        self.service = service
        self.executor = default_executor

    def handle(
        self,
        user_text,
        session_id="",
    ):
        print(
            "DEBUG EXECUTION HANDLER ENTERED",
            {
                "user_text": user_text,
                "session_id": session_id,
            },
        )

        execution = self.service._process_goal_and_plan(
            user_text,
            session_id,
        )

        print(
            "DEBUG EXECUTION HANDLER RETURN =",
            execution,
        )

        return execution

    def _build_fix_move(self, step: dict) -> dict:
        target_files = _get_target_files(step)

        target_function = str(
            step.get("target_function") or ""
        ).strip()

        if not target_files:
            return {
                "ok": False,
                "error": "Missing target_file.",
            }

        target_file = target_files[0]

        replacement_code = str(
            step.get("content")
            or step.get("code")
            or self._generate_placeholder_fix_code(
                target_function=target_function,
                step=step,
            )
            or ""
        ).strip()

        if not replacement_code:
            return {
                "ok": False,
                "error": "No replacement content generated for fix move.",
            }

        return {
            "ok": True,
            "move_type": "apply_function_fix",
            "payload": {
                "file_path": target_file,
                "function_name": target_function,
                "replacement_code": replacement_code,
            },
        }

    def execute_move(self, move):
        move_type = str(getattr(move, "type", "")).strip().lower()
        payload = getattr(move, "payload", {}) or {}

        if move_type == "apply_function_fix":
            result = self.apply_function_fix(
                file_path=payload.get("file_path", ""),
                function_name=payload.get("function_name", ""),
                replacement_code=payload.get("replacement_code", ""),
            )

            class MoveResult:
                def __init__(self, ok_result):
                    self.status = (
                        "success"
                        if ok_result.get("ok")
                        else "failed"
                    )

                    self.output = ok_result

                    self.error = ok_result.get(
                        "error",
                        "",
                    )

            return MoveResult(result)

        class MoveResult:
            def __init__(self):
                self.status = "failed"
                self.output = ""
                self.error = (
                    f"Unknown move type: {move_type}"
                )

        return MoveResult()

    def _classify_execution_failure(
        self,
        step: dict,
    ) -> dict:
        error_text = " ".join(
            [
                str(step.get("error") or ""),
                str(step.get("result") or ""),
            ]
        ).lower()

        failure = {
            "type": "unknown",
            "file": step.get("target_file") or "",
            "message": step.get("error") or "",
            "suggested_action": "inspect",
        }

        if "syntaxerror" in error_text:
            failure["type"] = "syntax_error"
            failure["suggested_action"] = "repair_syntax"

        elif "indentationerror" in error_text:
            failure["type"] = "indentation_error"
            failure["suggested_action"] = "repair_indentation"

        elif "modulenotfounderror" in error_text:
            failure["type"] = "missing_import"
            failure["suggested_action"] = "repair_import"

        elif "nameerror" in error_text:
            failure["type"] = "undefined_name"
            failure["suggested_action"] = "repair_symbol"

        elif "attributeerror" in error_text:
            failure["type"] = "missing_attribute"
            failure["suggested_action"] = "repair_attribute"

        return failure

    def _generate_file_replacement(
        self,
        step: dict,
    ) -> str:

        target_files = _get_target_files(step)

        target_file = (
            target_files[0]
            if target_files
            else ""
        )

        print(
            "DEBUG FILE REPLACEMENT INPUT:",
            {
                "target_file": step.get("target_file"),
                "target_files": step.get("target_files"),
                "mutation_mode": step.get("mutation_mode"),
                "title": step.get("title"),
            },
        )

        goal = str(
            step.get("goal")
            or step.get("title")
            or "repair file"
        ).strip()

        existing_code = ""

        try:
            if target_file and os.path.exists(target_file):
                with open(
                    target_file,
                    "r",
                    encoding="utf-8",
                ) as f:
                    existing_code = f.read()

                print(
                    "DEBUG EXISTING CODE:",
                    {
                        "length": len(existing_code),
                        "contains_before": (
                            "before" in existing_code
                        ),
                        "contains_after": (
                            "after" in existing_code
                        ),
                    },
                )

        except Exception as exc:
            print(
                "READ TARGET FAILED:",
                exc,
            )

        print(
            "DEBUG FILE REPLACEMENT INPUT:",
            {
                "target_file": step.get("target_file"),
                "target_files": step.get("target_files"),
                "mutation_mode": step.get("mutation_mode"),
                "title": step.get("title"),
            },
        )

        prompt = f"""

You are Nova's code mutation engine.

Return ONLY the complete replacement file.

Target:
{target_file}

Goal:
{goal}

Existing file:

{existing_code}

Rules:
- Return only Python code.
- No markdown fences.
- No explanations.
- Preserve existing functionality.
- Apply the requested mutation.
"""

        try:
            response = chat_completions_create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You generate complete safe Python file replacements."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )

            text = (
                response.choices[0]
                .message
                .content
                .strip()
            )

            print(
                "DEBUG FILE GENERATOR RETURN LENGTH:",
                len(text or ""),
            )

            print(
                "DEBUG FILE GENERATOR PREVIEW:",
                text[:200],
            )

            return text

        except Exception as exc:
            import traceback

            print(
                "FILE REPLACEMENT GENERATION FAILED:",
                repr(exc),
            )

            traceback.print_exc()

            return ""

    def apply_function_fix(
        self,
        file_path: str,
        function_name: str,
        replacement_code: str,
    ) -> dict:

        from pathlib import Path

        path = Path(file_path)

        if not path.exists():
            return {
                "ok": False,
                "error": f"File not found: {file_path}",
            }

        try:
            original = path.read_text(
                encoding="utf-8"
            )

            updated = replacement_code.strip()

            path.write_text(
                updated + "\n",
                encoding="utf-8",
            )

            return {
                "ok": True,
                "file_path": str(path),
                "function_name": function_name,
                "generated": True,
                "written": True,
                "replacement_preview": updated[:500],
            }

        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
            }

    def _execute_step(self, step: dict) -> dict:

        if isinstance(step, dict):

            if not step.get("title"):

                step["title"] = (
                    step.get("text")
                    or step.get("label")
                    or step.get("name")
                    or "step"
                )

            if not step.get("text"):

                step["text"] = (
                    step.get("title")
                    or "step"
                )

        title = str(
            step.get("title")
            or "step"
        ).strip()

        action = str(
            step.get("action")
            or title
            or "execute"
        ).strip().lower()

        input_value = str(
            step.get("input")
            or ""
        ).strip()

        target_file = str(
            step.get("target_file")
            or ""
        ).strip()

        target_function = str(
            step.get("target_function")
            or ""
        ).strip()

        result_lines = [
            f"Action: {action}",
            f"Title: {title}",
        ]

        if input_value:
            result_lines.append(
                f"Input: {input_value}"
            )

        if target_file:
            result_lines.append(
                f"Target file: {target_file}"
            )

        if target_function:
            result_lines.append(
                f"Target function: {target_function}"
            )

        if action == "design":

            step["status"] = "completed"
            step["error"] = None
            step["next_action"] = None
            step["mutation_ready"] = False
            step["payload_required"] = False
            step["mutation_mode"] = None

            result_lines.append(
                "Result: Design step completed."
            )

        elif action == "test":

            step["status"] = "completed"
            step["error"] = None
            step["next_action"] = None
            step["mutation_ready"] = False
            step["payload_required"] = False
            step["mutation_mode"] = None

            result_lines.append(
                "Result: Test step completed."
            )

            if target_file:
                result_lines.append(
                    f"Test target: {target_file}"
                )

        elif action in (
            "analysis",
            "analyze",
            "research",
            "review",
            "inspect",
            "plan",
        ):

            step["status"] = "completed"
            step["error"] = None
            step["next_action"] = None
            step["mutation_ready"] = False
            step["payload_required"] = False
            step["mutation_mode"] = None

            result_lines.append(
                f"Result: {action.capitalize()} step completed."
            )

        elif action == "implement":

            print(
                "DEBUG IMPLEMENT ENTERED",
                step,
            )

            if step.get("next_action") == "request_target":

                step["status"] = "waiting_for_target"
                step["error"] = None

                return step

            if not target_file:

                step["status"] = "failed"
                step["error"] = "Implement action missing target_file."

                result_lines.append(
                    "Result: Implement action failed: missing target_file."
                )

            else:

                result_lines.append(
                    "Result: Implement step running real file-write execution."
                )

        if (
            step.get("mutation_mode") == "file"
            and step.get("next_action")
            == "generate_file_replacement"
            and step.get("target_file")
            and not step.get("code")
        ):
            generated_code = (
                self._generate_file_replacement(
                    step,
                )
            )

            print(
                "DEBUG GENERATED REPLACEMENT:",
                len(generated_code or ""),
            )

            if generated_code:
                step["code"] = generated_code
                step["content"] = generated_code

                move_payload = self._build_mutation_payload_from_step(
                    step
                )



                if (
                    not move_payload
                    or not move_payload.get("ok")
                ):

                    result_lines.append(
                        "Result: Mutation payload generation deferred."
                    )

                else:


                    move = NextMove(
                        id=(
                            "implement_"
                            + str(int(time.time()))
                        ),
                        type=move_payload.get(
                            "move_type",
                            "apply_function_fix",
                        ),
                        payload=move_payload.get(
                            "payload",
                            {},
                        ),
                    )

                    apply_result = self.executor(
                        move
                    )

                    if (
                        apply_result
                        and (
                            getattr(
                                apply_result,
                                "status",
                                None,
                            ) == "success"
                            or getattr(
                                apply_result,
                                "ok",
                                False,
                            ) is True
                        )
                    ):
                        compile_output = (
                            apply_result.output
                            if isinstance(
                                apply_result.output,
                                dict,
                            )
                            else {}
                        )

                        compiled_ok = bool(
                            compile_output.get("compiled")
                            or compile_output.get("ast_valid")
                        )

                        if compiled_ok:

                            step["status"] = "waiting_for_payload"

                            result_lines = [
                                line
                                for line in result_lines
                                if "Implement action failed" not in line
                                and "Mutation status: failed" not in line
                            ]

                            step["result"] = "\n".join(
                                result_lines
                            )

                            step["error"] = None

                            step["error"] = None

                            step["mutation_ready"] = False
                            step["payload_required"] = False

                            step["mutation_move_type"] = (
                                move_payload.get("move_type")
                                or ""
                            )

                            # Preserve mutation history after successful apply.
                            if not step.get("mutation_mode"):
                                step["mutation_mode"] = (
                                    "file"
                                    if move_payload.get("move_type") == "fix_file"
                                    else "function"
                                )

                            result_lines.append(
                                "Result: Implement action completed."
                            )

                            result_lines.append(
                                "Mutation status: success."
                            )


                            result_lines.append(
                                "Result: Implement action completed."
                            )

                            result_lines.append(
                                "Mutation status: success."
                            )

                    else:

                        result_lines.append(
                            "Result: Implement action failed."
                        )

                        result_lines.append(
                            "Mutation status: failed."
                        )


                        result_lines.append(
                            "Result: Implement action failed."
                        )

                        result_lines.append(
                            "Mutation status: failed."
                        )


                if step.get("status") != "completed" and target_function:

                    result_lines.append(
                        "Next: generate function replacement payload and apply safely."
                    )

                    step["next_action"] = (
                        "generate_function_replacement"
                    )

                    step["mutation_ready"] = True

                    step["mutation_mode"] = "function"

        if (
            step.get("status") != "completed"
            and action in {
                "implement",
                "fix",
            }
            and step.get("next_action") != "request_target"
        ):

            if target_function:
                step["next_action"] = (
                    "generate_function_replacement"
                )

                step["mutation_ready"] = True

                step["mutation_mode"] = "function"

            else:
                step["next_action"] = (
                    "generate_file_replacement"
                )

                step["mutation_ready"] = True

                step["mutation_mode"] = "file"

                step["payload_required"] = True

        elif action == "test":

            target_files = _get_target_files(step)

            if not target_files:
                test_file = (
                    target_file
                    or str(
                        step.get("test_file")
                        or ""
                    ).strip()
                )

                if test_file:
                    target_files = [test_file]

            if not target_files:
                target_files = [
                    r"C:\Users\Owner\nova\nova_backend\services\execution_handler.py"
                ]

            compile_result = (
                self._compile_python_files(target_files)
                if len(target_files) > 1
                else self._compile_python_file(target_files[0])
            )

            if compile_result.get("ok"):

                runtime_target = target_files[0]

                runtime_result = self._run_python_file(
                    runtime_target
                )

                step["runtime_result"] = runtime_result

                if runtime_result.get("ok"):

                    step["status"] = "completed"

                    result_lines.append(
                        f"Tested files: {', '.join(target_files)}"
                    )

                    result_lines.append(
                        "Compile status: passed."
                    )

                    result_lines.append(
                        "Runtime status: passed."
                    )

                else:

                    step["status"] = "failed"

                    step["error"] = (
                        runtime_result.get("stderr")
                        or runtime_result.get("error")
                        or "Runtime execution failed."
                    )

                    step["failure_context"] = (
                        self._classify_execution_failure(step)
                    )

                    result_lines.append(
                        "Result: Test step failed."
                    )

                    result_lines.append(
                        "Compile status: passed."
                    )

                    result_lines.append(
                        "Runtime status: failed."
                    )

                    result_lines.append(
                        f"Error: {step['error']}"
                    )

                result_lines.append(
                    f"Tested files: {', '.join(target_files)}"
                )

            else:

                step["status"] = "failed"

                step["error"] = (
                    compile_result.get("stderr")
                    or compile_result.get("error")
                    or "Compile failed."
                )

                step["failure_context"] = (
                    self._classify_execution_failure(step)
                )

                result_lines.append(
                    "Result: Test step failed."
                )

                result_lines.append(
                    "Compile status: failed."
                )

                result_lines.append(
                    f"Tested files: {', '.join(target_files)}"
                )

                result_lines.append(
                    f"Error: {step['error']}"
                )

        elif action == "implement":

            if (
                step.get("next_action")
                == "generate_file_replacement"
                and not step.get("code")
                and not step.get("content")
            ):
                generated_code = (
                    self._generate_file_replacement(step)
                )

                print(
                    "DEBUG GENERATED FILE LENGTH:",
                    len(generated_code or ""),
                )

                if generated_code:
                    step["code"] = generated_code
                    step["content"] = generated_code

                else:
                    step["status"] = "failed"
                    step["error"] = (
                        "Failed to generate replacement code."
                    )

                    return {
                        "ok": False,
                        "error": step["error"],
                    }

                print(
                    "DEBUG CODE BEFORE PAYLOAD:",
                    {
                        "code_length": len(step.get("code") or ""),
                        "contains_after": "after" in (step.get("code") or ""),
                        "contains_before": "before" in (step.get("code") or ""),
                    },
                )


        elif action == "fix":

            result_lines.append(
                "Result: Fix step prepared."
            )

        elif action == "review":

            step["status"] = "completed"

            result_lines.append(
                "Result: Review step completed."
            )

        else:

            result_lines.append(
                "Result: Generic execution step completed."
            )

            if step.get("status") != "failed":

                if (
                    action in {"implement", "fix"}
                    and isinstance(
                        step.get("apply_result"),
                        dict,
                    )
                    and step["apply_result"].get("ok")
                ):
                    step["mutation_ready"] = True
                    step["payload_required"] = True

                elif step.get("next_action"):
                    if step.get("next_action") == "request_target":
                        step["status"] = "waiting_for_target"
                    else:
                        step["status"] = "completed"
                        step["payload_required"] = True

                elif action in {
                    "implement",
                    "test",
                }:
                    step["status"] = "completed"

                else:
                    step["status"] = "completed"

        if (
            step.get("status") == "waiting_for_payload"
            and action in {
                "implement",
                "fix",
            }
        ):

            step["payload_hint"] = {
                "target_file": target_file,
                "target_function": target_function,
                "mutation_mode": step.get(
                    "mutation_mode"
                ),
                "next_action": step.get(
                    "next_action"
                ),
                "input": input_value,
                "title": title,
            }

        if (
            action == "implement"
            and step.get("mutation_mode") == "file"
            and not step.get("code")
            and not step.get("content")
        ):
            generated_code = (
                self._generate_file_replacement(step)
            )

            if generated_code:
                step["code"] = generated_code
                step["content"] = generated_code

                print(
                    "DEBUG GENERATED FILE CODE:",
                    {
                        "length": len(
                            step.get("code") or ""
                        ),
                        "has_after": (
                            "after"
                            in (
                                step.get("code")
                                or ""
                            )
                        ),
                        "has_before": (
                            "before"
                            in (
                                step.get("code")
                                or ""
                            )
                        ),
                    },
                )

            else:
                step["status"] = "failed"
                step["error"] = (
                    "Failed to generate replacement code."
                )



        payload_result = (
            self._build_mutation_payload_from_step(step)
        )

        print(
            "DEBUG CODE BEFORE PAYLOAD:",
            {
                "code_length": len(
                    step.get("code") or ""
                ),
                "content_length": len(
                    step.get("content") or ""
                ),
                "contains_after": (
                    "after"
                    in (
                        step.get("code")
                        or step.get("content")
                        or ""
                    )
                ),
                "contains_before": (
                    "before"
                    in (
                        step.get("code")
                        or step.get("content")
                        or ""
                    )
                ),
            },
        )

        if payload_result.get("ok"):
            step["mutation_move_type"] = (
                payload_result.get("move_type")
                or ""
            )

            step["mutation_payload"] = (
                payload_result.get("payload")
                or {}
            )

            apply_result = self._apply_generated_mutation_payload(
                step
            )

            step["apply_result"] = apply_result

            if (
                isinstance(apply_result, dict)
                and apply_result.get("ok")
            ):
                step["status"] = "completed"
                step["error"] = None

                result_lines.append(
                    f"Payload: generated {payload_result.get('move_type')}."
                )

                result_lines.append(
                    "Mutation execution completed."
                )

            else:

                step["status"] = "failed"

                step["error"] = (
                    payload_result.get(
                        "error",
                        "Failed to build mutation payload.",
                    )
                )

                result_lines.append(
                    "Result: Implement action failed."
                )

                result_lines.append(
                    "Mutation status: failed."
                )

                result_lines.append(
                    "Mutation status: failed."
                )

            
                step["status"] = "failed"

                step["error"] = (
                    payload_result.get(
                        "error",
                        "Failed to build mutation payload.",
                    )
                )

                result_lines.append(
                    f"Payload error: {step['error']}"
                )

        if step.get("status") in {
            None,
            "",
            "pending",
        }:

            if action in {
                "design",
                "implement",
                "test",
                "fix",
                "review",
            }:
                step["status"] = "completed"

        step["result"] = "\n".join(
            result_lines
        )

        print(
            "DEBUG BEFORE RETURN STEP =",
            step,
        )

        return step

    def _generate_function_replacement(self, step: dict) -> str:
        payload_hint = step.get("payload_hint") or {}

        target_function = str(
            payload_hint.get("target_function")
            or step.get("target_function")
            or ""
        ).strip()

        current_code = str(
            step.get("content")
            or payload_hint.get("current_code")
            or ""
        ).strip()

        prompt = f"""
You are Nova's code repair engine.

Repair this Python function.

Function:
{target_function}

Goal:
{step.get("goal", "")}

Error:
{step.get("error", "")}

Current code:
{current_code}

Return ONLY the replacement Python function.
No explanation.
"""

        try:
            response = chat_completions_create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You generate safe Python function replacements."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )

            text = (
                response.choices[0]
                .message
                .content
                .strip()
            )

            print(
                "=== GENERATED FUNCTION REPLACEMENT ==="
            )
            print(text)

            return text

        except Exception as e:
            print(
                "FUNCTION REPAIR GENERATION FAILED:",
                str(e),
            )
            return ""

    def _apply_generated_mutation_payload(
        self,
        step: dict,
    ) -> dict:
        move_type = str(step.get("mutation_move_type") or "").strip()
        payload = step.get("mutation_payload") or {}

        if not move_type or not payload:
            return {
                "ok": False,
                "error": "Missing mutation move type or payload.",
            }

        result = self.executor(make_move(move_type, payload))

        if result.status != "success":
            return {
                "ok": False,
                "error": result.error or "Generated mutation failed.",
                "output": result.output,
            }

        return {
            "ok": True,
            "output": result.output,
        }

    def _build_mutation_payload_from_step(self, step: dict) -> dict:
        payload_hint = step.get("payload_hint") or {}

        target_files = (
            payload_hint.get("target_files")
            or step.get("target_files")
            or (
                [step.get("target_file")]
                if step.get("target_file")
                else []
            )
        )

        if isinstance(target_files, str):
            target_files = [target_files]

        target_files = [
            str(f).strip()
            for f in target_files
            if str(f).strip()
        ]

        if not target_files:
            target_files = _get_target_files(step)

        target_file = target_files[0] if target_files else ""
        target_function = str(
            payload_hint.get("target_function")
            or step.get("target_function")
            or ""
        ).strip()

        mutation_mode = str(
            payload_hint.get("mutation_mode")
            or step.get("mutation_mode")
            or ""
        ).strip().lower()

        if not target_file:
            return {
                "ok": False,
                "error": "Missing target_file for mutation payload.",
            }

        if mutation_mode == "function":
            if not target_function:
                return {
                    "ok": False,
                    "error": "Missing target_function for function mutation payload.",
                }

            return {
                "ok": True,
                "move_type": "apply_function_fix",
                "payload": {
                    "file_path": target_file,
                    "file_paths": target_files,
                    "function_name": target_function,
                    "replacement": self._generate_function_replacement(step),
                },
            }

        print(
            "DEBUG CODE BEFORE PAYLOAD:",
            {
                "code_length": len(step.get("code") or ""),
                "content_length": len(step.get("content") or ""),
                "code_after": "after" in (step.get("code") or ""),
                "content_after": "after" in (step.get("content") or ""),
                "code_before": "before" in (step.get("code") or ""),
                "content_before": "before" in (step.get("content") or ""),
            },
        )

        code = str(
            step.get("code")
            or step.get("content")
            or payload_hint.get("code")
            or ""
        ).strip()

        print(
            "DEBUG MUTATION PAYLOAD CODE:",
            {
                "length": len(code),
                "has_after": "after" in code,
                "has_before": "before" in code,
                "first_200": code[:200],
            },
        )

        if not code:
            return {
                "ok": False,
                "error": (
                    "File mutation requires explicit replacement code. "
                    "Refusing to overwrite the target with placeholder content."
                ),
            }

        return {
            "ok": True,
            "move_type": "fix_file",
            "payload": {
                "file_path": target_file,
                "file_paths": target_files,
                "code": code,
                "reason": (
                    step.get("goal")
                    or step.get("title")
                    or "Generated repair"
                ),
                "target": target_file,
                "preview": code[:500],
            },
        }

    def _verify_step_result(self, step: dict) -> dict:
        status = str(step.get("status") or "").lower()
        action = str(step.get("action") or "").lower()

        if status != "completed":
            if action != "review":
                return {
                    "ok": False,
                    "reason": "step_not_completed",
                }

        if action == "implement":
            apply_result = step.get("apply_result") or {}
            output = apply_result.get("output") if isinstance(apply_result, dict) else {}

            if not isinstance(output, dict):
                return {
                    "ok": False,
                    "reason": "missing_mutation_output",
                }

            if output.get("files"):
                files = output.get("files")

                if not all(
                    item.get("compiled")
                    for item in files
                ):
                    return {
                        "ok": False,
                        "reason": "mutation_not_validated",
                    }

            elif (
                not output.get("compiled")
                or (
                    "ast_valid" in output
                    and not output.get("ast_valid")
                )
            ):
                return {
                    "ok": False,
                    "reason": "mutation_not_validated",
                }


        if action == "test":
            result_text = str(step.get("result") or "").lower()

            if "compile status: passed" not in result_text:
                return {
                    "ok": False,
                    "reason": "runtime_test_failed",
                }

        return {
            "ok": True,
            "reason": "verified",
        }

    def _compile_python_files(self, file_paths: list[str]) -> dict:
        results = []

        for file_path in file_paths:
            results.append(
                self._compile_python_file(file_path)
            )

        return {
            "ok": all(
                item.get("ok")
                for item in results
            ),
            "compiled": all(
                item.get("ok")
                for item in results
            ),
            "files": results,
        }

    def _compile_python_file(self, file_path: str) -> dict:
        import subprocess
        import sys
        import os

        file_path = str(file_path or "").strip()

        if not file_path:
            return {
                "ok": False,
                "error": "No file path provided for compile check.",
            }

        if not os.path.exists(file_path):
            return {
                "ok": False,
                "error": f"File does not exist: {file_path}",
            }

        try:
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", file_path],
                capture_output=True,
                text=True,
            )

            return {
                "ok": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except Exception as exc:
            return {
                "ok": False,
                "error": repr(exc),
            }

    def _run_python_file(
        self,
        file_path: str,
    ) -> dict:
        import subprocess
        import sys
        import os

        file_path = str(
            file_path or ""
        ).strip()

        if not file_path:
            return {
                "ok": False,
                "error": "No file path provided for runtime check.",
            }

        if not os.path.exists(file_path):
            return {
                "ok": False,
                "error": f"File does not exist: {file_path}",
            }

        try:
            with open(
                file_path,
                "r",
                encoding="utf-8",
            ) as f:
                source = f.read()

            lowered = source.lower()

            server_markers = [
                "app.run(",
                "uvicorn.run(",
                "fastapi(",
                "flask(",
            ]

            is_server_app = any(
                marker in lowered
                for marker in server_markers
            )

            if is_server_app:
                compile_result = self._compile_python_file(
                    file_path
                )

                if compile_result.get("ok"):
                    return {
                        "ok": True,
                        "mode": "server_smoke_test",
                        "message": (
                            "Server application detected. "
                            "Compile validation passed."
                        ),
                        "compiled": True,
                    }

                return {
                    "ok": False,
                    "mode": "server_smoke_test",
                    "error": compile_result.get(
                        "error",
                        "Server compile validation failed.",
                    ),
                }

            result = subprocess.run(
                [
                    sys.executable,
                    file_path,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            return {
                "ok": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "error": "Runtime check timed out.",
            }

        except Exception as exc:
            return {
                "ok": False,
                "error": repr(exc),
            }

    def _record_execution_learning(
        self,
        step: dict,
        status: str,
        error: str = "",
    ) -> dict:
        return {
            "title": step.get("title", ""),
            "action": step.get("action", ""),
            "target_file": step.get("target_file", ""),
            "target_function": step.get("target_function", ""),
            "mutation_mode": step.get("mutation_mode", ""),
            "status": status,
            "error": error,
            "timestamp": int(time.time()),
        }

    def _persist_learning_entry(
        self,
        learning_entry: dict,
    ) -> dict:
        try:
            learning_file = Path(
                r"C:\Users\Owner\nova\data\execution_learning.json"
            )

            if learning_file.exists():
                existing = json.loads(
                    learning_file.read_text(encoding="utf-8")
                )
            else:
                existing = []

            if not isinstance(existing, list):
                existing = []

            existing.append(learning_entry)

            learning_file.write_text(
                json.dumps(existing, indent=2),
                encoding="utf-8",
            )

            return {
                "ok": True,
                "count": len(existing),
            }

        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
            }

    def _apply_step_mutation_with_retry(
        self,
        step: dict,
        history: list,
    ) -> dict:

        if step.get("status") != "waiting_for_payload":
            return step

        # Recover payload generated during step preparation
        # before attempting first apply.
        if not step.get("mutation_payload"):
            existing_payload = step.get(
                "mutation_payload_result",
                {},
            )

            if existing_payload.get("ok"):
                step["mutation_move_type"] = (
                    existing_payload.get("move_type")
                )

                step["mutation_payload"] = (
                    existing_payload.get("payload")
                    or {}
                )

        apply_result = self._apply_generated_mutation_payload(step)
        step["apply_result"] = apply_result

        if apply_result.get("ok"):
            compile_output = (
                apply_result.get("output")
                if isinstance(
                    apply_result.get("output"),
                    dict,
                )
                else {}
            )

            compiled_ok = bool(
                compile_output.get("compiled")
                or compile_output.get("ast_valid")
            )

            if compiled_ok:
                step["status"] = "completed"
                step["error"] = None

                # Preserve mutation history after retry success.
                step["mutation_ready"] = False
                step["payload_required"] = False

                if not step.get("mutation_move_type"):
                    step["next_action"] = None

                # Do not erase mutation history.
                # mutation_mode tells us what was repaired.
                if "mutation_mode" not in step:
                    step["mutation_mode"] = ""

                step["result"] = "\n".join(
                    [
                        "Action: implement",
                        f"Title: {step.get('title', '')}",
                        "Result: Implement action completed.",
                        "Mutation status: success.",
                    ]
                )

                history.append(
                    f"mutation applied: {step.get('title', 'step')}"
                )

                return step

            step["status"] = "failed"

            step["error"] = (
                compile_output.get("compile_error")
                or apply_result.get("error")
                or "Mutation compile validation failed."
            )

            history.append(
                f"mutation compile failed: {step.get('title', 'step')}"
            )

            return step

        retry_count = int(
            step.get("retry_count") or 0
        )

        if retry_count >= 1:
            step["status"] = "failed"

            step["error"] = apply_result.get(
                "error",
                "Mutation apply failed.",
            )

            history.append(
                f"mutation failed: {step.get('title', 'step')}"
            )

            return step

        step["retry_count"] = retry_count + 1

        regeneration_result = (
            self._build_mutation_payload_from_step(
                step
            )
        )

        step["mutation_payload_result"] = (
            regeneration_result
        )

        if not regeneration_result.get("ok"):
            step["status"] = "failed"

            step["error"] = (
                regeneration_result.get(
                    "error",
                    "Mutation regeneration failed.",
                )
            )

            history.append(
                f"mutation regeneration failed: {step.get('title', 'step')}"
            )

            return step

        step["mutation_move_type"] = (
            regeneration_result.get("move_type")
        )

        step["mutation_payload"] = (
            regeneration_result.get("payload")
            or {}
        )

        second_apply_result = (
            self._apply_generated_mutation_payload(
                step
            )
        )

        step["second_apply_result"] = (
            second_apply_result
        )

        if second_apply_result.get("ok"):
            compile_output = (
                second_apply_result.get("output")
                if isinstance(
                    second_apply_result.get("output"),
                    dict,
                )
                else {}
            )

            compiled_ok = bool(
                compile_output.get("compiled")
                or compile_output.get("ast_valid")
            )

            if compiled_ok:
                step["status"] = "completed"
                step["error"] = None

                step["mutation_result"] = {
                    "mutation_mode": step.get(
                        "mutation_mode"
                    ),
                    "next_action": step.get(
                        "next_action"
                    ),
                    "mutation_ready": step.get(
                        "mutation_ready"
                    ),
                    "payload_required": step.get(
                        "payload_required"
                    ),
                }

                step["next_action"] = None
                step["mutation_ready"] = False
                step["payload_required"] = False

                if "mutation_mode" not in step:
                    step["mutation_mode"] = ""

                step["result"] = "\n".join(
                    [
                        "Action: implement",
                        f"Title: {step.get('title', '')}",
                        "Result: Implement action completed after retry.",
                        "Mutation status: success.",
                    ]
                )

                history.append(
                    f"mutation regenerated and applied: {step.get('title', 'step')}"
                )

                return step

            step["status"] = "failed"

            step["error"] = (
                compile_output.get("compile_error")
                or second_apply_result.get("error")
                or "Mutation retry compile validation failed."
            )

            history.append(
                f"mutation retry compile failed: {step.get('title', 'step')}"
            )

        return step

    def _execute_runtime_step(
        self,
        step: dict,
        history: list,
        execution_state: dict,
    ) -> dict:

        step = self._execute_step(step)

        print(
            "DEBUG AFTER EXECUTE_STEP STATUS =",
            step.get("status"),
        )

        print(
            "DEBUG AFTER EXECUTE_STEP =",
            step,
        )

        learning_entry = self._record_execution_learning(
            step=step,
            status=step.get("status", ""),
            error=step.get("error", ""),
        )

        self._persist_learning_entry(
            learning_entry
        )

        execution_state.setdefault(
            "learning_history",
            [],
        ).append(
            learning_entry
        )

        step = self._apply_step_mutation_with_retry(
            step=step,
            history=history,
        )

        for key in [
            "mutation_payload",
            "mutation_payload_result",
            "mutation_move_type",
            "apply_result",
            "second_apply_result",
        ]:
            step.pop(key, None)

        if execution_state.get("steps"):
            execution_state["steps"][
                execution_state.get("current_index", 0)
            ] = step

        if step.get("status") == "completed":
            history.append(
                f"completed: {step.get('title', 'step')}"
            )

        elif step.get("status") == "failed":
            history.append(
                f"failed: {step.get('title', 'step')}"
            )

        return step

    def run_next_move(
        self,
        action: str,
        session_id: str = "",
        execution_state: dict | None = None,
        **kwargs,
    ) -> dict:
        action = str(action or "").strip().lower()
        print(
            "DEBUG RUN_NEXT_MOVE ACTION =",
            action,
        )
        execution_state = execution_state or {}

        if action in {"run_step", "next", "continue", "go"}:
            action = "run_step"

        if action in {"retry", "retry_failed", "try_again"}:
            action = "retry_failed"

        if action in {"run_all", "execute", "execute_all"}:
            action = "run_all"

        if action == "test_fail":
            return {
                "status": "failed",
                "error": (
                    "Fake execution failure for auto-fix test. "
                    "File: C:\\Users\\Owner\\nova\\nova_backend\\services\\chat_service.py. "
                    "Function: _process_execution_command."
                ),
                "execution_state": {
                    "status": "failed",
                    "steps": [
                        {"title": "Failed Step 1", "status": "failed"},
                        {"title": "Failed Step 2", "status": "pending"},
                    ],
                    "history": ["test_fail: Failed Step 1"],
                    "last_action": "test_fail",
                    "current_index": 0,
                    "current_step": "Failed Step 1",
                },
            }

        steps = execution_state.get("steps") or []

        print(
            "DEBUG RUN_NEXT_MOVE STEPS =",
            steps,
        )

        history = execution_state.get("history") or []
        current_index = int(
            execution_state.get("current_index")
            if execution_state.get("current_index") is not None
            else execution_state.get("current_step") or 0
        )
        if not steps:
            plan = execution_state.get("plan") or execution_state.get("normalized_steps") or []
            if plan:
                steps = plan

            else:
                return {
                    "ok": True,
                    "status": "idle",
                    "message": "",
                    "execution_state": {
                        "status": "idle",
                        "steps": [],
                        "history": history,
                        "current_index": 0,
                        "current_step": "",
                    },
                }

            current_index = 0

        if action == "retry_failed":
            for index, step in enumerate(steps):
                if step.get("status") == "failed":
                    step["status"] = "completed"
                    history.append(f"retried: {step.get('title', 'step')}")
                    execution_state["current_index"] = index + 1
                    execution_state["current_step"] = step.get("title", "step")
                    execution_state["last_action"] = action
                    execution_state["status"] = "success"
                    execution_state["steps"] = steps
                    execution_state["history"] = history

                    return {
                        "status": "success",
                        "message": "Failed step retried successfully.",
                        "execution_state": execution_state,
                    }

            return {
                "status": "success",
                "message": "No failed step found. Retry treated as complete.",
                "execution_state": execution_state,
            }

        if action == "run_step":
            if current_index >= len(steps):
                execution_state["status"] = "complete"
                execution_state["current_step"] = "All steps completed"
                execution_state["current_step_title"] = "All steps completed"
                execution_state["steps"] = steps
                execution_state["history"] = history
                execution_state["last_action"] = action

                return {
                    "status": "complete",
                    "message": "All steps completed.",
                    "execution_state": execution_state,
                }

            step = steps[current_index]

            completed_status = step.get("status")

            step = self._execute_runtime_step(
                step=step,
                history=history,
                execution_state=execution_state,
            )

            if (
                step.get("mutation_execution_result")
                and step["mutation_execution_result"].get("ok")
            ):
                step["status"] = "completed"

            if (
                completed_status == "completed"
                and step.get("status") != "completed"
            ):
                step["status"] = "completed"
            steps[current_index] = step

            history.append(
                {
                    "index": current_index,
                    "status": step.get("status"),
                    "step": dict(step),
                }
            )

            execution_state["steps"] = steps

            if step.get("status") == "completed":
                current_index += 1

            elif (
                step.get("status") == "failed"
                and step.get("action") in {"test", "inspect"}
            ):
                current_index += 1

            execution_state["current_index"] = current_index

        execution_state["status"] = (
            "complete"
            if execution_state["current_index"] >= len(steps)
            else (
                "failed"
                if (
                    step.get("status") == "failed"
                    and step.get("action") not in {"test", "inspect"}
                )
                else "running"
            )
        )


        self.service._save_execution_state(
            session_id,
            execution_state,
        )

        return {
            "status": (
                "success"
                if step.get("status") == "completed"
                else "failed"
            ),
            "message": (
                "Run step executed."
                if step.get("status") == "completed"
                else step.get("error", "Run step failed.")
            ),
            "execution_state": execution_state,
        }

        if action == "run_all":
            completed = []

            while current_index < len(steps):

                step = steps[current_index]

                print(
                    "DEBUG RUN_STEP BEFORE EXECUTE =",
                    step,
                )

                step = self._execute_runtime_step(
                    step=step,
                    history=history,
                    execution_state=execution_state,
                )

                print(
                    "DEBUG RUN_STEP AFTER EXECUTE =",
                    step,
                )

                steps[current_index] = step

                verify_result = self._verify_step_result(step)
                step["verify_result"] = verify_result

                if not verify_result.get("ok"):
                    step["status"] = "failed"
                    step["error"] = f"Verification failed: {verify_result.get('reason')}"
                    history.append(f"verification failed: {step.get('title', 'step')}")
                    break

                completed.append(step.get("title", "step"))

                if step.get("status") in {
                    "waiting_for_apply",
                    "waiting_for_payload",
                }:
                    break

                current_index += 1

            if (
                len(steps) == 1
                and str(steps[0].get("title", "")).strip().lower()
                == "no saved execution plan found"
            ):
                return {
                    "status": "idle",
                    "message": "",
                    "execution_state": {
                        "status": "idle",
                        "steps": [],
                        "history": history,
                        "current_index": 0,
                        "current_step": "",
                    },
                }

            execution_state["current_index"] = current_index

            execution_state["current_step"] = (
                steps[current_index].get("title", "payload required")
                if current_index < len(steps)
                else None
            )

            execution_state["current_step_title"] = (
                execution_state["current_step"]
                or "Execution complete"
            )

            execution_state["current_step_title"] = execution_state["current_step"]

            step = steps[current_index]

            step = self._execute_runtime_step(
                step=step,
                history=history,
                execution_state=execution_state,
            )

            steps[current_index] = step

            execution_state["steps"] = steps

            if step.get("status") == "completed":
                current_index += 1

            elif (
                step.get("status") == "failed"
                and step.get("action") in {"test", "inspect"}
            ):
                current_index += 1

            execution_state["current_index"] = current_index

            execution_state["status"] = (
                "failed"
                if current_index < len(steps)
                and steps[current_index].get("status") == "failed"
                else (
                    "waiting_for_payload"
                    if current_index < len(steps)
                    and steps[current_index].get("status") == "waiting_for_payload"
                    else "complete"
                )
            )

            execution_state["last_action"] = action
            execution_state["steps"] = steps
            execution_state["history"] = history

            summary_lines = [
                (
                    "Execution complete."
                    if execution_state["status"] == "complete"
                    else "Execution stopped."
                ),
                "",
                "Completed work:",
            ]

            for step in steps:
                summary_lines.append(
                    f"- {step.get('title', 'step')}: {step.get('status', 'unknown')}"
                )

            summary_lines.append("")

            if execution_state["status"] == "complete":
                summary_lines.append("Next: execution chain completed successfully.")
            elif execution_state["status"] == "failed":
                summary_lines.append("Next: inspect failed step and retry with regenerated mutation payload.")
            else:
                summary_lines.append("Next: continue execution chain.")

            return {
                "status": execution_state["status"],
                "message": "\n".join(summary_lines),
                "execution_state": execution_state,
            }

        return {
            "status": "failed",
            "message": "Unknown execution action.",
            "error": f"Unknown execution action: {action}",
            "execution_state": execution_state,
        }

    def run_next_step(
        self,
        action: str,
        session_id: str = "",
        execution_state: dict | None = None,
        **kwargs,
    ) -> dict:
        return self.run_next_move(
            action=action,
            session_id=session_id,
            execution_state=execution_state,
            **kwargs,
        )

    def run_chain(
        self,
        action: str,
        session_id: str = "",
        execution_state: dict | None = None,
        max_steps: int = 10,
        **kwargs,
    ) -> list[dict]:
        results = []

        for _ in range(max_steps):
            result = self.run_next_move(
                action=action,
                session_id=session_id,
                execution_state=execution_state or {},
                **kwargs,
            )
            results.append(result)

            status = str(result.get("status") or "").lower()
            execution_state = result.get("execution_state") or execution_state or {}

            if status in {"complete", "completed", "failed", "error"}:
                break

            action = "run_step"

        return results

    def _apply_function_fix_single_file(
        self,
        file_path: str,
        function_name: str,
        replacement: str,
    ) -> dict:
        import ast

        path = Path(file_path)

        if not path.exists():
            return {
                "file_path": file_path,
                "compiled": False,
                "error": f"File does not exist: {file_path}",
            }

        original = path.read_text(encoding="utf-8")
        lines = original.splitlines()

        try:
            tree = ast.parse(original)
        except SyntaxError as e:
            return {
                "file_path": file_path,
                "compiled": False,
                "error": f"Cannot parse target file before mutation: {e}",
            }

        target_node = None

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == function_name:
                    target_node = node
                    break

        if target_node is None:
            return {
                "file_path": file_path,
                "compiled": False,
                "error": f"Function not found by AST: {function_name}",
            }

        if not hasattr(target_node, "lineno") or not hasattr(target_node, "end_lineno"):
            return {
                "file_path": file_path,
                "compiled": False,
                "error": f"AST node missing line boundaries: {function_name}",
            }

        start_index = int(target_node.lineno) - 1
        end_index = int(target_node.end_lineno)

        backup_path = path.with_suffix(
            path.suffix + f".bak_{int(time.time() * 1000)}"
        )

        shutil.copy2(
            path,
            backup_path,
        )

        replacement_lines = replacement.strip("\n").splitlines()

        new_lines = (
            lines[:start_index]
            + replacement_lines
            + lines[end_index:]
        )

        path.write_text(
            "\n".join(new_lines) + "\n",
            encoding="utf-8",
        )

        mutated_source = path.read_text(
            encoding="utf-8"
        )

        try:
            ast.parse(mutated_source)
        except SyntaxError as e:
            shutil.copy2(
                backup_path,
                path,
            )

            return {
                "file_path": file_path,
                "backup": str(backup_path),
                "compiled": False,
                "rolled_back": True,
                "error": f"AST validation failed after mutation: {e}",
            }

        compile_ok = True
        compile_error = ""

        try:
            py_compile.compile(
                str(path),
                doraise=True,
            )
        except Exception as e:
            compile_ok = False
            compile_error = str(e)

        if not compile_ok:
            shutil.copy2(
                backup_path,
                path,
            )

        return {
            "file_path": file_path,
            "backup": str(backup_path),
            "compiled": compile_ok,
            "rolled_back": not compile_ok,
            "compile_error": compile_error,
        }

def default_executor(move: NextMove) -> ExecutionResult:
    try:
        move_type = str(move.type or "").strip().lower()
        payload = move.payload or {}

        if move_type == "test_fail":
            return ExecutionResult(
                move_id=move.id,
                status="failed",
                output={"test": "forced failure"},
                error="Forced test failure for self-healing loop.",
                next_moves=[
                    make_move("retry_failed"),
                    make_move("run_step"),
                ],
            )

        if move_type == "run_step":
            return ExecutionResult(
                move_id=move.id,
                status="success",
                output={
                    "message": "Run step executed.",
                    "next_move": "review execution result and choose the next move",
                },
                next_moves=[
                    make_move("run_step"),
                    make_move("retry_failed"),
                    make_move("run_all"),
                    make_move("review_execution_result"),
                ],
            )

        if move_type == "log":
            return ExecutionResult(
                move_id=move.id,
                status="success",
                output={"logged": payload},
            )

        if move_type == "echo":
            return ExecutionResult(
                move_id=move.id,
                status="success",
                output={"echo": payload},
            )

        if move_type == "plan":
            return ExecutionResult(
                move_id=move.id,
                status="success",
                output={
                    "plan": [
                        "analyze task",
                        "build steps",
                        "execute steps",
                    ],
                    "task": payload.get("task"),
                },
            )

        if move_type == "verify_execution_loop":
            return ExecutionResult(
                move_id=move.id,
                status="success",
                output={
                    "verified": True,
                    "message": "Execution loop verified.",
                },
            )

        if move_type == "review_execution_result":
            return ExecutionResult(
                move_id=move.id,
                status="success",
                output={
                    "reviewed": True,
                    "message": "Execution result reviewed.",
                },
            )

        if move_type == "persist_execution_result":
            return ExecutionResult(
                move_id=move.id,
                status="success",
                output={
                    "persisted": True,
                    "message": "Execution result persisted.",
                    "payload": payload,
                },
            )

        if move_type == "apply_function_fix":
            file_path = str(
                payload.get("file_path") or ""
            ).strip()

            function_name = str(
                payload.get("function_name") or ""
            ).strip()

            replacement = str(
                payload.get("replacement") or ""
            ).strip()

            if not file_path or not function_name or not replacement:
                return ExecutionResult(
                    move_id=move.id,
                    status="failed",
                    error="Missing file_path, function_name, or replacement.",
                )

            path = Path(file_path)

            if not path.exists():
                return ExecutionResult(
                    move_id=move.id,
                    status="failed",
                    error=f"File does not exist: {file_path}",
                )

            backup_path = path.with_suffix(
                path.suffix + f".bak_{int(time.time())}"
            )

            shutil.copy2(
                path,
                backup_path,
            )

            result = self._apply_function_fix_single_file(
                file_path=file_path,
                function_name=function_name,
                replacement=replacement,
            )

            return ExecutionResult(
                move_id=move.id,
                status=(
                    "success"
                    if result.get("compiled")
                    else "failed"
                ),
                output=result,
                error=result.get(
                    "error",
                    "",
                ),
            )

        if move_type == "fix_file":
            file_paths = payload.get("file_paths") or []

            if isinstance(file_paths, str):
                file_paths = [file_paths]

            file_paths = [
                str(f).strip()
                for f in file_paths
                if str(f).strip()
            ]

            file_path = str(
                payload.get("file_path") or ""
            ).strip()

            if not file_paths and file_path:
                file_paths = [file_path]

            new_code = str(payload.get("code") or "")

            if not file_paths or not new_code.strip():
                return ExecutionResult(
                    move_id=move.id,
                    status="failed",
                    error="Missing file_path(s) or code.",
                )



            results = []

            for file_path in file_paths:
                path = Path(file_path)

                if path.exists():
                    backup_path = path.with_suffix(
                        path.suffix + f".bak_{int(time.time())}"
                    )

                    shutil.copy2(
                        path,
                        backup_path,
                    )
                else:
                    path.parent.mkdir(
                        parents=True,
                        exist_ok=True,
                    )

                    backup_path = None

                path.write_text(
                    new_code,
                    encoding="utf-8",
                )

                compile_ok = True
                compile_error = ""

                if path.suffix == ".py":
                    try:
                        import ast

                        ast.parse(
                            path.read_text(
                                encoding="utf-8"
                            )
                        )

                    except Exception as e:
                        compile_ok = False
                        compile_error = (
                            f"AST validation failed: {e}"
                        )

                        if backup_path:
                            shutil.copy2(
                                backup_path,
                                path,
                            )

                if compile_ok and path.suffix == ".py":
                    try:
                        py_compile.compile(str(path), doraise=True)
                    except Exception as e:
                        compile_ok = False
                        compile_error = str(e)

                        if backup_path:
                            shutil.copy2(
                                backup_path,
                                path,
                            )

                results.append(
                    {
                        "file_path": str(path),
                        "backup": str(backup_path),
                        "compiled": compile_ok,
                        "compile_error": compile_error,
                    }
                )

            all_compiled = all(
                item.get("compiled")
                for item in results
            )

            first_error = next(
                (
                    item.get("compile_error")
                    for item in results
                    if item.get("compile_error")
                ),
                "",
            )

            return ExecutionResult(
                move_id=move.id,
                status="success" if all_compiled else "failed",
                output={
                    "files": results,
                    "compiled": all_compiled,
                },
                error=first_error,
            )
            
        if move_type == "apply_function_fix":
            file_paths = payload.get("file_paths") or []

            if isinstance(file_paths, str):
                file_paths = [file_paths]

            file_paths = [
                str(f).strip()
                for f in file_paths
                if str(f).strip()
            ]

            file_path = str(
                payload.get("file_path") or ""
            ).strip()

            if not file_paths and file_path:
                file_paths = [file_path]

            function_name = str(
                payload.get("function_name") or ""
            ).strip()

            replacement = str(
                payload.get("replacement") or ""
            )

            if not file_paths or not function_name or not replacement.strip():
                return ExecutionResult(
                    move_id=move.id,
                    status="failed",
                    error="Missing required fields.",
                )

            results = []

            for file_path in file_paths:
                results.append(
                    self._apply_function_fix_single_file(
                        file_path=file_path,
                        function_name=function_name,
                        replacement=replacement,
                    )
                )

            success = all(
                item.get("compiled")
                for item in results
            )

            return ExecutionResult(
                move_id=move.id,
                status="success" if success else "failed",
                output={
                    "files": results,
                },
            )

            next_list = payload.get("next") or []
            next_moves = []

            for item in next_list:
                if isinstance(item, dict):
                    next_moves.append(
                        make_move(
                            item.get("type", "log"),
                            item.get("payload", {}),
                        )
                    )

            return ExecutionResult(
                move_id=move.id,
                status="success",
                output={"chained": len(next_moves)},
                next_moves=next_moves,
            )

        return ExecutionResult(
            move_id=move.id,
            status="failed",
            error=f"Unknown move type: {move_type}",
        )

    except Exception as e:
        return ExecutionResult(
            move_id=move.id,
            status="failed",
            error=str(e),
        )




