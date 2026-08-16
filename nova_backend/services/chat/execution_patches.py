def _nova_clean_goal_for_planner_20260609(value: str) -> str:
    text = str(value or "").strip()

    prefixes = (
        "auto-plan ",
        "autoplan ",
        "plan ",
        "build ",
        "create ",
        "make ",
        "implement ",
        "fix ",
        "repair ",
        "upgrade ",
    )

    lowered = text.lower()

    for prefix in prefixes:
        if lowered.startswith(prefix):
            return text[len(prefix):].strip() or "generic"

    return text or "generic"


def _nova_build_planner_fallback_state_20260609(goal_text: str) -> dict:
    return {
        "goal": str(goal_text or "").strip(),
        "steps": [],
        "status": "pending",
    }


def _nova_clean_goal_for_planner_20260609(value: str) -> str:
    text = str(value or "").strip()

    prefixes = (
        "auto-plan ",
        "autoplan ",
        "plan ",
        "build ",
        "create ",
        "make ",
        "implement ",
        "fix ",
        "repair ",
        "upgrade ",
    )

    lowered = text.lower()

    for prefix in prefixes:
        if lowered.startswith(prefix):
            return text[len(prefix):].strip() or "generic"

    return text or "generic"


def _nova_build_planner_fallback_state_20260609(goal_text: str) -> dict:
    safe_goal = _nova_clean_goal_for_planner_20260609(goal_text)

    if _nova_planner_service_20260609 is None:
        steps = [
            f"Design the approach for {safe_goal}.",
            f"Implement the solution for {safe_goal}.",
            f"Test and verify {safe_goal}.",
        ]
        planner_available = False
    else:
        try:
            steps = _nova_planner_service_20260609.build_execution_steps(safe_goal)
            planner_available = True
        except Exception:
            steps = [
                f"Design the approach for {safe_goal}.",
                f"Implement the solution for {safe_goal}.",
                f"Test and verify {safe_goal}.",
            ]
            planner_available = False

    steps = [
        str(step or "").strip()
        for step in (steps or [])
        if str(step or "").strip()
    ]

    if not steps:
        steps = [
            f"Design the approach for {safe_goal}.",
            f"Implement the solution for {safe_goal}.",
            f"Test and verify {safe_goal}.",
        ]

    return {
        "status": "ready",
        "goal": safe_goal,
        "original_user_text": str(goal_text or ""),
        "steps": steps,
        "current_index": 0,
        "current_step": steps[0] if steps else None,
        "current_step_title": steps[0] if steps else None,
        "history": [],
        "waiting": False,
        "complete": False,
        "error": None,
        "planner_service_used": planner_available,
        "planner_fallback": True,
        "source": "planner_service",
    }

def install_chat_service_runtime_patches():
    install_project_brain_patch(ChatService)

    try:
        install_execution_planner_runtime_patches()
    except Exception:
        pass

    try:
        install_token_usage_finalize_wrapper(ChatService)
    except Exception:
        pass

    try:
        install_non_web_source_leak_guard(ChatService)
    except Exception:
        pass

    try:
        install_attachment_web_suppression()
    except Exception:
        pass


def install_execution_planner_runtime_patches(ChatService):
    """
    Disabled.

    Execution planning is now handled by:
    nova_backend.services.execution.service.ExecutionService

    Do not override:
        ChatService._process_goal_and_plan

    The ExecutionHandler flow owns planner execution.
    """

    return