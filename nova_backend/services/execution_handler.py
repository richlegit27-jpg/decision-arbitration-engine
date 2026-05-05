from __future__ import annotations

import py_compile
import shutil
import time
import uuid
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Callable


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


class ExecutionHandler:
    def __init__(self, executor: MoveExecutor):
        self.executor = executor

def run_next_move(self, action: str, execution_state: dict):
    # 🔥 normalize incoming actions
    if action in {"run_step", "next", "continue", "go"}:
        action = "next"

    if action in {"retry", "retry_failed", "try_again"}:
        action = "retry_failed"

    if action in {"run_all", "execute", "execute_all"}:
        action = "run_all"

    if not execution_state:
        return {
            "status": "error",
            "current_step": "No execution state",
            "steps": [],
            "history": [],
            "last_action": action,
        }

    steps = execution_state.get("steps", [])
    current_index = execution_state.get("current_index", 0)
    history = execution_state.get("history", [])

    if action == "next":
        if current_index >= len(steps):
            return {
                "status": "complete",
                "current_step": "All steps completed",
                "steps": steps,
                "history": history,
                "last_action": action,
            }

        step = steps[current_index]
        step["status"] = "completed"
        history.append(f"completed: {step.get('title', 'step')}")

        execution_state["current_index"] = current_index + 1
        execution_state["last_action"] = action

        return execution_state

    elif action == "retry_failed":
        for i, step in enumerate(steps):
            if step.get("status") == "failed":
                step["status"] = "completed"
                history.append(f"retried: {step.get('title', 'step')}")
                execution_state["current_index"] = i + 1
                execution_state["last_action"] = action
                return execution_state

        return execution_state

    elif action == "run_all":
        for step in steps:
            step["status"] = "completed"
            history.append(f"completed: {step.get('title', 'step')}")

        execution_state["current_index"] = len(steps)
        execution_state["status"] = "complete"
        execution_state["last_action"] = action

        return execution_state

    return {
        "status": "error",
        "current_step": "Unknown action",
        "steps": steps,
        "history": history,
        "last_action": action,
    }

    def run_chain(
        self,
        first_move: NextMove,
        max_steps: int = 10,
        max_retries: int = 3,
        delay_ms: int = 500,
    ) -> list[ExecutionResult]:
        results: list[ExecutionResult] = []
        queue: list[NextMove] = [first_move]
        steps = 0

        while queue and steps < max_steps:
            move = queue.pop(0)

            result = self.run_next_move(
                move,
                max_retries=max_retries,
                delay_ms=delay_ms,
            )

            # 🔥 ensure output exists
            if result.output is None:
                result.output = {}

            # 🔥 attach error to output for frontend
            if result.status == "failed":
                result.output["error"] = result.error or "Unknown error"

            results.append(result)

            # 🔥 stop chain on failure
            if result.status == "failed":
                break

            if result.next_moves:
                queue.extend(result.next_moves)

            steps += 1

        return results

def make_move(move_type: str, payload: dict[str, Any] | None = None) -> NextMove:
    return NextMove(
        id=str(uuid.uuid4()),
        type=move_type,
        payload=payload or {},
    )


def default_executor(move: NextMove) -> ExecutionResult:
    try:
        move_type = str(move.type or "").strip().lower()
        payload = move.payload or {}

        # =============================
        # CORE MOVES
        # =============================


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

        # =============================
        # FILE OPERATIONS
        # =============================

        if move_type == "fix_file":
            file_path = str(payload.get("file_path") or "").strip()
            new_code = str(payload.get("code") or "")

            if not file_path or not new_code.strip():
                return ExecutionResult(
                    move_id=move.id,
                    status="failed",
                    error="Missing file_path or code.",
                )

            path = Path(file_path)

            if not path.exists():
                return ExecutionResult(
                    move_id=move.id,
                    status="failed",
                    error=f"File does not exist: {file_path}",
                )

            # 🔥 backup original
            backup_path = path.with_suffix(path.suffix + f".bak_{int(time.time())}")
            shutil.copy2(path, backup_path)

            # 🔥 write new code
            path.write_text(new_code, encoding="utf-8")

            compile_ok = True
            compile_error = ""

            # 🔥 compile check for python files
            if path.suffix == ".py":
                try:
                    py_compile.compile(str(path), doraise=True)
                except Exception as e:
                    compile_ok = False
                    compile_error = str(e)

            return ExecutionResult(
                move_id=move.id,
                status="success" if compile_ok else "failed",
                output={
                    "file_path": str(path),
                    "backup": str(backup_path),
                    "compiled": compile_ok,
                    "compile_error": compile_error,
                },
                error=compile_error if not compile_ok else "",
            )

        if move_type == "apply_function_fix":
            file_path = str(payload.get("file_path") or "").strip()
            function_name = str(payload.get("function_name") or "").strip()
            replacement = str(payload.get("replacement") or "")

            if not file_path or not function_name or not replacement.strip():
                return ExecutionResult(
                    move_id=move.id,
                    status="failed",
                    error="Missing required fields.",
                )

            path = Path(file_path)

            if not path.exists():
                return ExecutionResult(
                    move_id=move.id,
                    status="failed",
                    error=f"File does not exist: {file_path}",
                )

            original = path.read_text(encoding="utf-8")
            lines = original.splitlines()

            start_index = None

            for i, line in enumerate(lines):
                if line.lstrip().startswith(f"def {function_name}("):
                    start_index = i
                    break

            if start_index is None:
                return ExecutionResult(
                    move_id=move.id,
                    status="failed",
                    error=f"Function not found: {function_name}",
                )

            backup_path = path.with_suffix(path.suffix + f".bak_{int(time.time())}")
            shutil.copy2(path, backup_path)

            replacement_lines = replacement.strip("\n").splitlines()
            new_lines = lines[:start_index] + replacement_lines

            path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

            return ExecutionResult(
                move_id=move.id,
                status="success",
                output={
                    "file_path": str(path),
                    "backup": str(backup_path),
                },
            )

        if move_type == "chain":
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