from __future__ import annotations

import time
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


MoveExecutor = Callable[[NextMove], ExecutionResult]


class ExecutionHandler:
    def __init__(self, executor: MoveExecutor):
        self.executor = executor

    def run_next_move(
        self,
        next_move: NextMove,
        max_retries: int = 3,
        delay_ms: int = 500,
    ) -> ExecutionResult:
        attempt = 0

        while attempt <= max_retries:
            try:
                result = self.executor(next_move)

                if result.status == "success":
                    return result

                if result.status != "retry":
                    return result

            except Exception as e:
                if attempt >= max_retries:
                    return ExecutionResult(
                        move_id=next_move.id,
                        status="failed",
                        error=str(e),
                    )

            attempt += 1
            time.sleep(delay_ms / 1000)

        return ExecutionResult(
            move_id=next_move.id,
            status="failed",
            error="Max retries exceeded.",
        )


def default_executor(move: NextMove) -> ExecutionResult:
    if move.type == "build_execution_loop":
        return ExecutionResult(
            move_id=move.id,
            status="success",
            output={
                "message": "Execution loop scaffold created.",
                "move_type": move.type,
                "payload": move.payload,
            },
        )

    return ExecutionResult(
        move_id=move.id,
        status="failed",
        error=f"No executor registered for move type: {move.type}",
    )