from __future__ import annotations

from nova_backend.services.code_workspace_service import CodeWorkspaceService
from nova_backend.tools.base import NovaTool


class CodeWorkspaceTool(NovaTool):
    """Read-only tool adapter; callers cannot select a path or Git command."""

    name = "code_workspace"
    description = "Read branch, working-tree, diff, and commit facts for Nova's configured repository. This tool is strictly read-only."
    category = "git"
    capabilities = ["repository status", "branch inspection", "working tree inspection", "commit history", "file diff"]
    risk_level = "low"
    requires_confirmation = False

    def __init__(self, service: CodeWorkspaceService | None = None):
        self.service = service or CodeWorkspaceService()

    def run(self, operation="snapshot", file="", revision="", staged=False, **kwargs):
        if kwargs.get("path") or kwargs.get("command"):
            return {"ok": False, "error": "arbitrary_paths_and_commands_not_supported"}
        if not isinstance(staged, bool):
            return {"ok": False, "error": "staged_must_be_boolean"}
        try:
            if operation == "snapshot":
                return {"ok": True, "snapshot": self.service.snapshot()}
            if operation == "diff" and file:
                return {"ok": True, "diff": self.service.file_diff(file, staged=staged)}
            if operation == "commit_detail" and revision:
                return {"ok": True, "commit": self.service.commit_details(revision)}
            return {"ok": False, "error": "unsupported_read_only_operation"}
        except Exception:
            return {"ok": False, "error": "repository_inspection_failed"}
