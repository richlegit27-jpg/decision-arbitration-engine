"""Bounded execution bridge for structured model tool calls."""

from __future__ import annotations

import json
import hashlib
import logging
from typing import Any, Callable

from nova_backend.tools.pending_tool_approval_service import pending_tool_approval_service


MAX_TOOL_ROUNDS = 3
MAX_TOOL_CALLS = 5
_logger = logging.getLogger("nova.tools")


def mutation_signature(tool_name: str, arguments: dict) -> str:
    payload = json.dumps(arguments, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256((str(tool_name) + payload).encode("utf-8")).hexdigest()


def should_offer_model_tools(user_text: str, decision: dict | None = None) -> bool:
    """Gate tool schemas to routed tool work, without choosing a tool by text."""
    decision = decision if isinstance(decision, dict) else {}
    if decision.get("tool_use") is True or decision.get("tools_enabled") is True:
        return True
    intent = " ".join(str(decision.get(key) or "") for key in ("route", "mode", "intent")).lower()
    if any(marker in intent for marker in ("code_workspace", "file_operation", "tool_use", "project_execution")):
        return True
    # This is only an availability gate: the model selects and parameterizes
    # tools through structured schemas, and the executor validates every call.
    text = str(user_text or "").lower()
    requests = (
        "read this file", "open this file", "list the files", "list files",
        "search this code", "search the code", "validate this json",
        "check this project directory", "check the project directory",
        "inspect this repository", "search my project",
    )
    return any(phrase in text for phrase in requests)


def _value(value: Any, key: str, default=None):
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def response_function_calls(response: Any) -> list[dict]:
    """Normalize Responses API function_call output items."""
    items = _value(response, "output", []) or []
    calls = []
    for item in items:
        if _value(item, "type") != "function_call":
            continue
        calls.append({
            "tool_name": str(_value(item, "name", "") or "").strip(),
            "arguments": _value(item, "arguments", "{}"),
            "call_id": str(_value(item, "call_id", "") or _value(item, "id", "") or "").strip(),
        })
    return calls


def execute_structured_call(
    call: dict,
    *,
    registry,
    executor,
    surface: str,
    session_id: str,
    owner_id: str,
    model_response_id: str = "",
    model: str = "",
) -> dict:
    """Validate a canonical call and route it through the shared executor."""
    name = str(call.get("tool_name") or "").strip()
    call_id = str(call.get("call_id") or "").strip()
    raw_arguments = call.get("arguments", {})
    try:
        arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
    except (TypeError, ValueError):
        return {"ok": False, "status": "validation_error", "error_category": "invalid_tool_input", "message": "Tool arguments were not valid JSON.", "retryable": False}
    if not isinstance(arguments, dict):
        return {"ok": False, "status": "validation_error", "error_category": "invalid_tool_input", "message": "Tool arguments must be a JSON object.", "retryable": False}
    metadata = registry.get_tool(name) if registry is not None else None
    if metadata is None or not metadata.get("implemented") or not metadata.get("available"):
        return {"ok": False, "status": "unavailable", "error_category": "tool_not_registered", "message": "That tool is not available.", "retryable": False}

    result = executor.run(name, arguments, confirm=False)
    if result.get("status") == "approval_required" or result.get("error_category") == "approval_required":
        if not owner_id or not session_id:
            return {"ok": False, "status": "approval_required", "error_category": "approval_required", "requires_approval": True, "message": "Approval is required before this action can run.", "retryable": False}
        pending_result = pending_tool_approval_service.set_pending(
            session_id,
            {
                "tool": name,
                "payload": arguments,
                "risk": metadata.get("risk_class", "WRITE"),
                "surface": surface,
                "call_id": call_id,
                "model_response_id": model_response_id,
                "model": model,
            },
            owner_id=owner_id,
        )
        if not pending_result.get("ok"):
            return {"ok": False, "status": "approval_required", "error_category": "approval_required", "requires_approval": True, "message": "Approval is required before this action can run.", "retryable": False}
        return {
            "ok": False,
            "status": "approval_required",
            "error_category": "approval_required",
            "requires_approval": True,
            "pending": True,
            "risk_class": metadata.get("risk_class", "WRITE"),
            "pending_tool": {"tool": name, "risk": metadata.get("risk_class", "WRITE"), "payload": arguments},
            "message": "Approval is required before this action can run.",
            "retryable": False,
        }

    # Do not let a model turn repeat a mutation after observing a failure.
    safe = dict(result)
    safe.setdefault("user_message", safe.get("summary") or safe.get("message") or "The tool finished.")
    safe.setdefault("technical_category", safe.get("error_category"))
    safe.setdefault("retryable", False)
    safe.setdefault("artifact_references", [])
    return safe


def run_responses_tool_loop(
    *,
    first_response: Any,
    model_call: Callable[[list[dict], str | None], Any],
    registry,
    executor,
    text_extractor: Callable[[Any], str],
    surface: str,
    session_id: str,
    owner_id: str,
    model: str = "",
    prior_mutation_signatures=None,
    max_rounds: int = MAX_TOOL_ROUNDS,
    max_calls: int = MAX_TOOL_CALLS,
) -> dict:
    """Run a bounded Responses API function-call loop; never retries tools."""
    response = first_response
    previous_id = _value(response, "id")
    tool_outputs: list[dict] = []
    seen_call_ids: set[str] = set()
    attempted_mutations: set[str] = set(prior_mutation_signatures or [])
    call_count = 0

    for _ in range(max(0, min(int(max_rounds), MAX_TOOL_ROUNDS))):
        calls = response_function_calls(response)
        if not calls:
            return {"text": text_extractor(response), "response": response, "tool_outputs": tool_outputs, "status": "completed"}

        outputs = []
        for call in calls:
            call_count += 1
            call_id = call.get("call_id") or ""
            if call_count > max_calls:
                return {"text": "I reached the safe limit for tool actions on this request.", "response": response, "tool_outputs": tool_outputs, "status": "limit_reached"}
            if not call_id or call_id in seen_call_ids:
                result = {"ok": False, "status": "validation_error", "error_category": "invalid_tool_input", "message": "This tool request was malformed or duplicated.", "retryable": False}
            else:
                seen_call_ids.add(call_id)
                metadata = registry.get_tool(call.get("tool_name")) if registry is not None else None
                mutation_key = ""
                if metadata and metadata.get("risk_class") != "READ":
                    try:
                        raw_args = call.get("arguments")
                        parsed_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                        mutation_key = mutation_signature(str(call.get("tool_name") or ""), parsed_args)
                    except (TypeError, ValueError):
                        mutation_key = ""
                if mutation_key and mutation_key in attempted_mutations:
                    result = {"ok": False, "status": "failed", "error_category": "tool_failed", "message": "Nova did not repeat the same write action during this request.", "retryable": False}
                else:
                    if mutation_key:
                        attempted_mutations.add(mutation_key)
                    result = execute_structured_call(
                        call,
                        registry=registry,
                        executor=executor,
                        surface=surface,
                        session_id=session_id,
                        owner_id=owner_id,
                        model_response_id=str(previous_id or ""),
                        model=model,
                    )
            tool_outputs.append({"tool_name": call.get("tool_name"), "call_id": call_id, "result": result})
            if result.get("status") == "approval_required":
                return {"text": result.get("message") or "Approval is required before this action can run.", "response": response, "tool_outputs": tool_outputs, "status": "approval_required"}
            outputs.append({
                "type": "function_call_output",
                "call_id": call_id,
                "output": json.dumps(result, ensure_ascii=False, default=str),
            })

        if not previous_id:
            return {"text": "The tool result could not be returned to the model.", "response": response, "tool_outputs": tool_outputs, "status": "provider_protocol_error"}
        try:
            response = model_call(outputs, str(previous_id))
        except Exception as exc:
            _logger.warning("tool continuation model call failed", extra={"error_type": type(exc).__name__})
            return {"text": "The tool finished, but Nova could not complete the response.", "response": response, "tool_outputs": tool_outputs, "status": "model_error"}
        previous_id = _value(response, "id")

    if response_function_calls(response):
        return {"text": "I reached the safe limit for tool steps on this request.", "response": response, "tool_outputs": tool_outputs, "status": "limit_reached"}
    return {"text": text_extractor(response), "response": response, "tool_outputs": tool_outputs, "status": "completed"}
