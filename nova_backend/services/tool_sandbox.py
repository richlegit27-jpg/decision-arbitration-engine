from __future__ import annotations

from nova_backend.services.python_runner_service import PythonRunnerService


class ToolSandbox:
    """Shared project-workspace path and command execution boundary."""

    PATH_FIELDS = {
        "file_read": ("path",), "file_write": ("path",), "file_append": ("path",),
        "file_delete": ("path",), "file_list": ("path",), "file_exists": ("path",),
        "file_info": ("path",), "file_move": ("source", "destination"),
        "file_copy": ("source", "destination"), "directory_create": ("path",),
        "directory_delete": ("path",), "directory_list": ("path",),
        "python_run": ("path",), "python_compile": ("path",),
        "code_search": ("path",), "code_replace": ("path",), "text_search": ("path",),
        "project_tree": ("path",), "disk_usage": ("path",),
    }
    DISABLED_COMMAND_TOOLS = {"shell_command", "terminal_execute", "python_run", "process_start"}

    def __init__(self, python_runner=None):
        self.python_runner = python_runner or PythonRunnerService()

    def validate_payload(self, tool_name, payload):
        if tool_name in self.DISABLED_COMMAND_TOOLS:
            return None, {
                "ok": False, "tool": tool_name, "status": "blocked",
                "error": "os_sandbox_unavailable",
                "summary": "Command and code execution tools are disabled until Nova provides an operating-system-enforced workspace sandbox.",
                "error_category": "sandbox_unavailable",
            }
        fields = self.PATH_FIELDS.get(tool_name)
        if not fields:
            return payload, None
        safe_payload = dict(payload)
        for field in fields:
            value = safe_payload.get(field)
            if value in (None, ""):
                continue
            try:
                resolved = self.python_runner.resolve_sandbox_path(value)
            except (OSError, TypeError, ValueError):
                resolved = None
            if resolved is None:
                return None, {
                    "ok": False, "tool": tool_name, "status": "blocked",
                    "error": "workspace_path_blocked",
                    "summary": "The requested path is outside Nova's configured workspace.",
                    "error_category": "sandbox_path_blocked",
                }
            safe_payload[field] = str(resolved)
        return safe_payload, None
