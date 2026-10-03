from __future__ import annotations


_RISK_BY_TOOL = {
    "file_read": ("READ", False), "file_list": ("READ", False),
    "file_exists": ("READ", False), "file_info": ("READ", False),
    "directory_list": ("READ", False), "code_search": ("READ", False),
    "text_search": ("READ", False), "memory_read": ("READ", False),
    "git_status": ("READ", False), "git_diff": ("READ", False),
    "git_log": ("READ", False), "git_show": ("READ", False),
    "file_write": ("WRITE", True), "file_append": ("WRITE", True),
    "file_copy": ("WRITE", True), "file_move": ("WRITE", True),
    "directory_create": ("WRITE", True), "code_replace": ("WRITE", True),
    "python_compile": ("WRITE", True), "memory_write": ("WRITE", True),
    "project_workspace_update": ("WRITE", True), "file_delete": ("DESTRUCTIVE", True),
    "directory_delete": ("DESTRUCTIVE", True), "memory_delete": ("DESTRUCTIVE", True),
    "shell_command": ("DESTRUCTIVE", True), "terminal_execute": ("DESTRUCTIVE", True),
    "python_run": ("DESTRUCTIVE", True), "process_start": ("DESTRUCTIVE", True),
    "process_stop": ("DESTRUCTIVE", True), "git_commit": ("DESTRUCTIVE", True),
    "email.send": ("EXTERNAL_ACTION", True), "calendar.create": ("EXTERNAL_ACTION", True),
    "session.rename": ("WRITE", True), "session.pin": ("WRITE", True),
    "session.delete": ("DESTRUCTIVE", True), "chat.send": ("READ", False),
    "attachment.upload": ("WRITE", True), "attachment.analyze": ("READ", False),
}


def tool_risk_metadata(tool_name: str, tool=None) -> dict:
    name = str(tool_name or "").strip().lower()
    default = _RISK_BY_TOOL.get(name)
    if default is None:
        raw = str(getattr(tool, "risk_level", "low") or "low").strip().lower()
        risk = {"low": "READ", "medium": "WRITE", "high": "DESTRUCTIVE", "critical": "EXTERNAL_ACTION"}.get(raw, "WRITE")
        # Any operation classified above READ must be approved, even if a
        # newly registered tool forgot to set its legacy confirmation flag.
        requires = risk != "READ" or bool(getattr(tool, "requires_confirmation", False))
    else:
        risk, requires = default
        requires = requires or bool(getattr(tool, "requires_confirmation", False))
    return {"risk_class": risk, "requires_approval": requires}


def tool_requires_approval(tool_name: str, tool=None) -> bool:
    return bool(tool_risk_metadata(tool_name, tool)["requires_approval"])


def step_requires_approval(step: dict) -> bool:
    if not isinstance(step, dict):
        return False
    if step.get("requires_approval") is True or step.get("approval_required") is True:
        return True
    names = [str(step.get(key) or "").strip().lower() for key in ("tool_name", "tool", "tool_action", "action", "operation")]
    if any(name and tool_requires_approval(name) for name in names):
        return True
    operation = " ".join(names + [str(step.get("command") or "").lower()])
    destructive = ("delete", "remove", "shell", "terminal", "python_run", "execute", "git push", "deploy", "email", "calendar", "paid", "write", "append", "copy", "move")
    return any(marker in operation for marker in destructive)
