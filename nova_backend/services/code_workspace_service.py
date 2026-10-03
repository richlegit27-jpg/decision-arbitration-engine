"""Read-only, repository-scoped Git intelligence for Nova."""

from __future__ import annotations

import os
import logging
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


logger = logging.getLogger(__name__)


class CodeWorkspaceError(RuntimeError):
    """A safe, user-displayable Code Workspace failure."""


class _GitText(str):
    def __new__(cls, value: str, *, truncated: bool = False):
        result = super().__new__(cls, value)
        result.truncated = truncated
        return result


class CodeWorkspaceService:
    """Expose bounded read-only Git facts for one configured repository.

    The root comes from trusted application configuration, never a chat
    argument. Set ``NOVA_CODE_WORKSPACE_ROOT`` to select another repository.
    """

    MAX_OUTPUT_CHARS = 24_000
    MAX_FILES_IN_SUMMARY = 40
    MAX_STATUS_ENTRIES = 200
    SENSITIVE_PATH = re.compile(
        r"(^|[/\\])(?:\.env(?:\..*)?|[^/\\]*(?:secret|credential|private.?key)[^/\\]*|id_rsa|[^/\\]*\.(?:pem|key))$",
        re.IGNORECASE,
    )
    SECRET_VALUE = re.compile(
        r"(?i)(\b(?:api[_-]?key|secret|password|token|credential)\b\s*[:=]\s*['\"]?)[A-Za-z0-9_./+=:-]{8,}"
    )

    def __init__(
        self,
        repository_root: str | os.PathLike[str] | None = None,
        *,
        timeout: float = 8.0,
        output_limit: int = MAX_OUTPUT_CHARS,
        runner: Callable[..., Any] | None = None,
    ) -> None:
        configured = repository_root or os.environ.get("NOVA_CODE_WORKSPACE_ROOT")
        self.root = Path(configured).expanduser().resolve() if configured else Path(__file__).resolve().parents[2]
        self.timeout = max(0.1, float(timeout))
        self.output_limit = max(256, int(output_limit))
        self._runner = runner
        self._git = shutil.which("git") or "git"

    @staticmethod
    def is_git_command_text(command: str) -> bool:
        """Recognize direct or path-qualified Git invocations in shell input."""
        return bool(re.search(r"(?i)\bgit(?:\.exe)?\b", str(command or "")))

    @staticmethod
    def classify_request(text: str) -> str | None:
        """Return ``read`` or ``blocked_mutation`` for repository-intent text."""
        value = " ".join(str(text or "").strip().lower().split())
        if not value:
            return None

        mutation = re.search(
            r"\bgit\s+(?:add|commit|push|pull|fetch|checkout|switch|restore|reset|merge|rebase|cherry-pick|stash|clean)\b|"
            r"\b(?:commit|push|pull|fetch|checkout|switch|restore|reset|merge|rebase|cherry[- ]pick|stash|stage|clean)\s+(?:this|it|them|these|changes|the changes|my changes|our changes|the branch|branch|these files|those files|to origin|from origin)\b",
            value,
        )
        repo_context = bool(re.search(r"\b(git|repo|repository|working tree|branch|commit|changes?)\b", value))
        lone_mutation = bool(re.fullmatch(r"(?:please\s+)?(?:git\s+)?(?:add|commit|push|pull|fetch|checkout|switch|restore|reset|merge|rebase|cherry-pick|stash|stage|clean)", value))
        if mutation or lone_mutation:
            return "blocked_mutation"

        read_markers = (
            "git status", "git diff", "git log", "git show", "git branch",
            "repository status", "repo status", "working tree",
            "what's changed in", "what changed in", "what changed recently",
            "which files are dirty", "dirty files", "untracked files", "staged files",
            "what branch", "current branch", "branch am i on", "repository root",
            "repo root", "last commit", "latest commit", "recent commits",
            "commit history", "last checkpoint", "what files did that commit change",
            "files changed in the last", "explain this diff", "show me what changed in",
            "what changed in", "safe to edit", "development state",
            "what did we change yesterday", "what did we change today",
            "what did we change recently", "what did we fix yesterday",
            "what did we fix today", "what happened in commit",
            "did we modify", "did we change", "was this file changed",
        )
        explicit_context = bool(re.search(r"\b(git|repo|repository|working tree|branch|commits?|diff|untracked|staged)\b", value))
        if re.search(r"\b(?:what happened|what changed|show|explain|inspect)\b.*\bcommit\s+[0-9a-f]{7,40}\b", value):
            return "read"
        retrospective = any(marker in value for marker in (
            "what did we change yesterday", "what did we change today",
            "what did we change recently", "what did we fix yesterday",
            "what did we fix today", "files changed in the last", "development state",
        ))
        component_change = bool(re.search(r"\b(?:did we (?:modify|change)|was this file changed|were changes made to)\b", value))
        component_context = bool(re.search(r"\b(project|execution|chat|session|billing|memory|auth|mobile|file|repository|repo)\b", value))
        file_context = bool(re.search(r"\b[a-z0-9_.-]+\.(?:py|js|ts|tsx|jsx|html|css|json|md|yml|yaml|toml)\b", value))
        if any(marker in value for marker in read_markers) and (explicit_context or file_context or retrospective or component_change and component_context or "what's changed in" in value or "what changed in" in value):
            return "read"
        return None

    def _run(
        self,
        *args: str,
        limit: int = 2_000_000,
        allow_truncation: bool = False,
    ) -> str:
        if not self.root.exists() or not self.root.is_dir():
            raise CodeWorkspaceError("The configured repository folder is unavailable.")

        command = [self._git, "-C", str(self.root), *args]
        env = os.environ.copy()
        for key in list(env):
            if key in {
                "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                "GIT_NAMESPACE", "GIT_PREFIX", "GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS",
            } or key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")):
                env.pop(key, None)
        env.update({
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_PAGER": "cat",
            # This environment-scoped exception is limited to the trusted,
            # configured root; it does not alter the user's Git config.
            "GIT_CONFIG_COUNT": "2",
            "GIT_CONFIG_KEY_0": "safe.directory",
            "GIT_CONFIG_VALUE_0": str(self.root),
            "GIT_CONFIG_KEY_1": "core.fsmonitor",
            "GIT_CONFIG_VALUE_1": "false",
        })
        try:
            if self._runner is not None:
                result = self._runner(
                    command,
                    cwd=str(self.root),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self.timeout,
                    check=False,
                    env=env,
                )
                if result.returncode:
                    raise CodeWorkspaceError("Nova couldn't read the configured Git repository.")
                output = str(result.stdout or "")
                truncated = len(output.encode("utf-8", errors="replace")) > limit
                output = output[:limit]
            else:
                with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
                    process = subprocess.Popen(
                        command,
                        cwd=str(self.root),
                        stdout=stdout_file,
                        stderr=stderr_file,
                        env=env,
                        shell=False,
                    )
                    started = time.monotonic()
                    truncated = False
                    while process.poll() is None:
                        output_size = os.fstat(stdout_file.fileno()).st_size
                        if output_size > limit:
                            truncated = True
                            process.terminate()
                            break
                        if time.monotonic() - started > self.timeout:
                            process.kill()
                            process.wait()
                            raise CodeWorkspaceError("Git took too long to answer. Please try again.")
                        time.sleep(0.02)
                    process.wait(timeout=1)
                    if process.returncode and not truncated:
                        raise CodeWorkspaceError("Nova couldn't read the configured Git repository.")
                    stdout_file.seek(0)
                    output = stdout_file.read(limit + 1).decode("utf-8", errors="replace")
                    truncated = truncated or len(output.encode("utf-8", errors="replace")) > limit
                    output = output[:limit]
            if truncated and not allow_truncation:
                raise CodeWorkspaceError("Git returned too much data. Ask for a specific file or a shorter history range.")
            return _GitText(output, truncated=truncated)
        except subprocess.TimeoutExpired as exc:
            raise CodeWorkspaceError("Git took too long to answer. Please try again.") from exc
        except FileNotFoundError as exc:
            raise CodeWorkspaceError("Git is not installed in this environment.") from exc
        except OSError as exc:
            raise CodeWorkspaceError("Nova couldn't read the repository right now.") from exc

    def _validate_repository(self) -> None:
        try:
            top = self._run("rev-parse", "--show-toplevel").strip()
        except CodeWorkspaceError as exc:
            if "not installed" in str(exc) or "too long" in str(exc):
                raise
            raise CodeWorkspaceError("The configured folder is not a Git repository.") from exc
        try:
            actual = Path(top).resolve()
        except OSError as exc:
            raise CodeWorkspaceError("The configured folder is not a Git repository.") from exc
        if actual != self.root:
            raise CodeWorkspaceError("The configured folder must be the repository root.")

    def _validated_file(self, file_path: str) -> str:
        raw = str(file_path or "").strip()
        if not raw or "\x00" in raw:
            raise CodeWorkspaceError("Give me a file path inside the selected repository.")
        candidate = Path(raw)
        candidate = (candidate if candidate.is_absolute() else self.root / candidate).resolve()
        try:
            relative = candidate.relative_to(self.root)
        except ValueError as exc:
            raise CodeWorkspaceError("That file is outside the selected repository.") from exc
        normalized = relative.as_posix()
        if self.SENSITIVE_PATH.search(normalized):
            raise CodeWorkspaceError("I can't display diffs for credential or private-key files.")
        return normalized

    def _parse_status(self) -> dict[str, Any]:
        raw = self._run("status", "--porcelain=v1", "--branch", "--untracked-files=all")
        lines = raw.splitlines()
        branch_summary = lines.pop(0)[3:].strip() if lines and lines[0].startswith("## ") else ""
        staged: list[str] = []
        unstaged: list[str] = []
        untracked: list[str] = []
        deleted: list[str] = []
        renamed: list[str] = []
        conflicted: list[str] = []
        modified: list[str] = []
        entries: list[dict[str, str]] = []
        for line in lines:
            if len(line) < 4:
                continue
            code = line[:2]
            path = line[3:]
            if " -> " in path:
                path = path.rsplit(" -> ", 1)[-1]
            entries.append({"status": code, "path": path})
            if code == "??":
                untracked.append(path)
                continue
            if code in {"DD", "AU", "UD", "UA", "DU", "AA", "UU"} or "U" in code:
                conflicted.append(path)
            if "R" in code:
                renamed.append(path)
            if "D" in code:
                deleted.append(path)
            if code[0] not in {" ", "?"}:
                staged.append(path)
            if code[1] not in {" ", "?"}:
                unstaged.append(path)
            if "M" in code or "A" in code:
                modified.append(path)
        return {
            "branch_summary": branch_summary,
            "entries": entries,
            "entry_count": len(entries),
            "staged_files": sorted(set(staged)),
            "unstaged_files": sorted(set(unstaged)),
            "untracked_files": sorted(set(untracked)),
            "deleted_files": sorted(set(deleted)),
            "renamed_files": sorted(set(renamed)),
            "conflicted_files": sorted(set(conflicted)),
            "modified_files": sorted(set(modified)),
        }

    def recent_commits(
        self,
        limit: int = 5,
        *,
        since: str | None = None,
        until: str | None = None,
    ) -> list[dict[str, str]]:
        limit = max(1, min(int(limit), 20))
        args = ["log", f"-{limit}"]
        if since in {"midnight", "yesterday"}:
            args.append(f"--since={since}")
        if until == "midnight":
            args.append("--until=midnight")
        args.append("--format=%H%x1f%h%x1f%an%x1f%cI%x1f%s")
        raw = self._run(*args)
        commits = []
        for line in raw.splitlines():
            parts = line.split("\x1f", 4)
            if len(parts) == 5:
                commits.append(dict(zip(("hash", "short_hash", "author", "date", "subject"), parts)))
        return commits

    def recent_changed_files(self, limit: int = 5) -> list[dict[str, Any]]:
        commits = self.recent_commits(limit)
        results = []
        for commit in commits:
            details = self.commit_details(commit["hash"])
            results.append({
                **commit,
                "files": details["files"],
                "file_count": details["file_count"],
            })
        return results

    def snapshot(self, recent_limit: int = 5) -> dict[str, Any]:
        self._validate_repository()
        status = self._parse_status()
        branch = self._run("branch", "--show-current").strip()
        head = self._run("rev-parse", "HEAD").strip()
        commits = self.recent_commits(recent_limit)
        files = status["entries"]
        status_summary = {
            "modified": len(status["modified_files"]),
            "staged": len(status["staged_files"]),
            "unstaged": len(status["unstaged_files"]),
            "deleted": len(status["deleted_files"]),
            "renamed": len(status["renamed_files"]),
            "untracked": len(status["untracked_files"]),
            "conflicted": len(status["conflicted_files"]),
        }
        entries_truncated = len(files) > self.MAX_STATUS_ENTRIES
        for key in ("entries", "staged_files", "unstaged_files", "untracked_files", "deleted_files", "renamed_files", "conflicted_files", "modified_files"):
            status[key] = status[key][: self.MAX_STATUS_ENTRIES]
        return {
            "repository_name": self.root.name,
            "repository_root": str(self.root),
            "branch": branch or "(detached HEAD)",
            "head_commit": head,
            "is_clean": status["entry_count"] == 0,
            **status,
            "files_truncated": entries_truncated,
            "recent_commits": commits,
            "summary": status_summary,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def file_diff(self, file_path: str | None = None, *, staged: bool = False) -> dict[str, Any]:
        self._validate_repository()
        relative = self._validated_file(file_path) if file_path else None
        args = ["diff", "--no-ext-diff", "--no-textconv", "--no-color"]
        if staged:
            args.append("--cached")
        if relative:
            args.extend(["--", relative])
        raw = self._run(*args, limit=self.output_limit + 1, allow_truncation=True)
        truncated = bool(getattr(raw, "truncated", False)) or len(raw) > self.output_limit
        text = raw[: self.output_limit]
        text = self.SECRET_VALUE.sub(r"\1[REDACTED]", text)
        text = re.sub(r"\bAKIA[0-9A-Z]{16}\b", "[REDACTED_AWS_KEY]", text)
        text = re.sub(r"\bsk-[A-Za-z0-9_-]{16,}\b", "[REDACTED_PROVIDER_KEY]", text)
        return {
            "file": relative,
            "staged": bool(staged),
            "diff": text,
            "has_changes": bool(raw.strip()),
            "original_chars": None if truncated else len(raw),
            "observed_chars": len(raw),
            "truncated": truncated,
            "output_limit": self.output_limit,
        }

    def largest_changed_files(self, limit: int = 10) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 20))
        totals: dict[str, dict[str, Any]] = {}
        for staged in (False, True):
            args = ["diff", "--numstat"]
            if staged:
                args.append("--cached")
            raw = self._run(*args)
            for line in raw.splitlines():
                parts = line.split("\t", 2)
                if len(parts) != 3:
                    continue
                added = int(parts[0]) if parts[0].isdigit() else 0
                removed = int(parts[1]) if parts[1].isdigit() else 0
                item = totals.setdefault(parts[2], {"file": parts[2], "added": 0, "removed": 0})
                item["added"] += added
                item["removed"] += removed
                item["changed"] = item["added"] + item["removed"]
        return sorted(totals.values(), key=lambda item: item["changed"], reverse=True)[:limit]

    def commit_details(self, revision: str) -> dict[str, Any]:
        value = str(revision or "").strip()
        if value.upper() == "HEAD":
            value = "HEAD"
        elif not re.fullmatch(r"(?:[0-9a-fA-F]{7,40}|HEAD~\d{1,3})", value):
            raise CodeWorkspaceError("Use a commit hash or HEAD to inspect a commit.")
        self._validate_repository()
        formatted = self._run("show", "--format=%H%x1f%h%x1f%an%x1f%cI%x1f%s", "--name-status", "--no-renames", value)
        lines = formatted.splitlines()
        meta = lines[0].split("\x1f", 4) if lines else []
        files = []
        for line in lines[1:]:
            parts = line.split("\t", 1)
            if len(parts) == 2:
                files.append({"status": parts[0], "path": parts[1]})
        files_truncated = len(files) > self.MAX_STATUS_ENTRIES
        return {
            "commit": dict(zip(("hash", "short_hash", "author", "date", "subject"), meta)) if len(meta) == 5 else {},
            "files": files[: self.MAX_STATUS_ENTRIES],
            "file_count": len(files),
            "files_truncated": files_truncated,
            "stat": self._run("show", "--format=", "--shortstat", value).strip(),
        }

    def commit_diff(self, revision: str, file_path: str | None = None) -> dict[str, Any]:
        value = str(revision or "").strip()
        if value.upper() == "HEAD":
            value = "HEAD"
        elif not re.fullmatch(r"(?:[0-9a-fA-F]{7,40}|HEAD~\d{1,3})", value):
            raise CodeWorkspaceError("Use a commit hash or HEAD to inspect a commit.")
        self._validate_repository()
        args = ["show", "--no-ext-diff", "--no-textconv", "--no-color", "--format=fuller", value]
        if file_path:
            args.extend(["--", self._validated_file(file_path)])
        raw = self._run(*args, limit=self.output_limit + 1, allow_truncation=True)
        truncated = bool(getattr(raw, "truncated", False)) or len(raw) > self.output_limit
        text = raw[: self.output_limit]
        text = self.SECRET_VALUE.sub(r"\1[REDACTED]", text)
        text = re.sub(r"\bAKIA[0-9A-Z]{16}\b", "[REDACTED_AWS_KEY]", text)
        text = re.sub(r"\bsk-[A-Za-z0-9_-]{16,}\b", "[REDACTED_PROVIDER_KEY]", text)
        return {
            "revision": value,
            "file": file_path,
            "diff": text,
            "original_chars": None if truncated else len(raw),
            "observed_chars": len(raw),
            "truncated": truncated,
            "output_limit": self.output_limit,
        }

    @staticmethod
    def _artifact_warning(path: str) -> bool:
        lowered = path.lower()
        return bool(
            re.search(r"(?:\.bak(?:kup)?|\.recovery-backup|\.tmp|\.log|\.cache)$", lowered)
            or re.search(r"(?:^|[/\\])(?:__pycache__|\.pytest_cache|\.mypy_cache|sandbox)(?:[/\\]|$)", lowered)
            or lowered.endswith("output.txt")
        )

    def answer_request(self, text: str) -> dict[str, Any]:
        kind = self.classify_request(text)
        if kind == "blocked_mutation":
            return {
                "ok": False,
                "kind": kind,
                "text": "Code Workspace is read-only right now. I can inspect Git changes and history, but I can't stage, commit, push, pull, reset, restore, or otherwise change this repository.",
            }
        if kind != "read":
            return {"ok": False, "kind": "unsupported", "text": "I couldn't identify a repository-inspection request."}

        try:
            snapshot = self.snapshot()
            lower = " ".join(str(text or "").lower().split())
            file_match = re.search(r"([\w.-]+(?:[/\\][\w.-]+)*\.[A-Za-z0-9_-]+)", str(text or ""))
            if file_match and any(marker in lower for marker in ("diff", "what changed", "changed in", "show me what changed")):
                file_result = self.file_diff(file_match.group(1))
                staged_result = self.file_diff(file_match.group(1), staged=True)
                combined = "\n".join(part["diff"] for part in (file_result, staged_result) if part["diff"])
                if combined:
                    response = f"Changes in `{file_result['file']}`:\n\n```diff\n{combined}\n```"
                    if file_result["truncated"] or staged_result["truncated"]:
                        response += "\n\nThe diff was shortened to fit. Ask for a narrower file or specific section to inspect more."
                    return {"ok": True, "kind": "file_diff", "snapshot": snapshot, "text": response, "diff": {**file_result, "staged_diff": staged_result["diff"]}}
                return {"ok": True, "kind": "file_diff", "snapshot": snapshot, "text": f"Git has no staged or unstaged diff for `{file_result['file']}`. Untracked files are listed separately and aren't included in `git diff` output."}

            if any(marker in lower for marker in ("git diff", "show changes", "explain this diff", "show me the diff")):
                unstaged = self.file_diff()
                staged = self.file_diff(staged=True)
                chunks = [part["diff"] for part in (unstaged, staged) if part["diff"]]
                combined = "\n".join(chunks)
                truncated = unstaged["truncated"] or staged["truncated"] or len(combined) > self.output_limit
                combined = combined[: self.output_limit]
                if combined:
                    response = f"Repository diff (read-only):\n\n```diff\n{combined}\n```"
                    if truncated:
                        response += "\n\nThe diff was shortened to fit. Ask for a specific file to inspect it more closely."
                else:
                    response = "There are no staged or unstaged tracked-file diffs. Untracked files are listed separately."
                return {"ok": True, "kind": "repository_diff", "snapshot": snapshot, "text": response, "diff": {"diff": combined, "truncated": truncated, "output_limit": self.output_limit}}

            if any(marker in lower for marker in ("last commit", "latest commit", "what was the last", "checkpoint", "what files did that commit change")):
                details = self.commit_details("HEAD")
                commit = details.get("commit", {})
                files = ", ".join(item["path"] for item in details["files"][:self.MAX_FILES_IN_SUMMARY]) or "no files"
                return {"ok": True, "kind": "commit_detail", "snapshot": snapshot, "text": f"Latest commit `{commit.get('short_hash', '')}` — {commit.get('subject', '')}\nAuthor: {commit.get('author', 'unknown')} · {commit.get('date', '')}\nFiles ({details['file_count']}): {files}"}

            if "files changed in the last" in lower or "files did those commits change" in lower:
                history = self.recent_changed_files(5)
                sections = []
                for commit in history:
                    file_list = ", ".join(item["path"] for item in commit["files"][:self.MAX_FILES_IN_SUMMARY]) or "no files"
                    sections.append(f"- `{commit['short_hash']}` {commit['subject']}: {file_list}")
                return {"ok": True, "kind": "history_files", "snapshot": snapshot, "text": "Files changed in the five most recent commits:\n" + ("\n".join(sections) or "- No commits found."), "commits": history}

            commit_match = re.search(r"\bcommit\s+([0-9a-fA-F]{7,40})\b", str(text or ""))
            if commit_match:
                details = self.commit_details(commit_match.group(1))
                commit = details.get("commit", {})
                files = ", ".join(item["path"] for item in details["files"][:self.MAX_FILES_IN_SUMMARY]) or "no files"
                response = f"Commit `{commit.get('short_hash', '')}` — {commit.get('subject', '')}\nAuthor: {commit.get('author', 'unknown')} · {commit.get('date', '')}\nFiles ({details['file_count']}): {files}"
                if any(marker in lower for marker in ("diff", "show changes", "what happened", "what changed")):
                    diff = self.commit_diff(commit_match.group(1))
                    response += f"\n\n```diff\n{diff['diff']}\n```"
                    if diff["truncated"]:
                        response += "\n\nThe commit diff was shortened to fit."
                return {"ok": True, "kind": "commit_detail", "snapshot": snapshot, "text": response, "commit": details}

            if "yesterday" in lower and ("change" in lower or "fix" in lower):
                recent_items = self.recent_commits(20, since="yesterday", until="midnight")
            elif "today" in lower and ("change" in lower or "fix" in lower):
                recent_items = self.recent_commits(20, since="midnight")
            else:
                recent_items = snapshot["recent_commits"]
            recent = "\n".join(f"- `{c['short_hash']}` {c['subject']} ({c['date']})" for c in recent_items)
            if any(marker in lower for marker in ("recent commits", "last five commits", "five recent", "commit history", "what did we change", "what changed recently")) and not any(marker in lower for marker in ("working tree", "untracked", "staged files", "dirty files")):
                return {"ok": True, "kind": "history", "snapshot": snapshot, "text": f"Recent repository commits:\n{recent or '- No commits found.'}"}

            component_match = re.search(r"\bdid we (?:modify|change)\s+(.+?)[?.!]*$", str(text or ""), re.IGNORECASE)
            if component_match:
                component = component_match.group(1).strip().strip("?.! ")
                terms = [word.lower() for word in re.findall(r"[A-Za-z0-9_-]+", component) if word.lower() not in {"the", "a", "an", "in", "on", "our", "my"}]
                matches = [entry["path"] for entry in snapshot["entries"] if any(term in entry["path"].lower() for term in terms)]
                if matches:
                    response = f"Current Git changes include {len(matches)} path(s) whose names match **{component}**:\n" + "\n".join(f"- `{path}`" for path in matches[:self.MAX_FILES_IN_SUMMARY])
                    response += "\n\nThis is based on changed paths; inspect the file diffs to confirm the exact behavior changed."
                else:
                    response = f"No currently changed path name matches **{component}**. That doesn't rule out related edits under differently named files."
                return {"ok": True, "kind": "component_change_check", "snapshot": snapshot, "text": response, "matching_files": matches}

            if any(marker in lower for marker in ("largest changes", "largest diffs", "biggest changes", "files contain the largest")):
                largest = self.largest_changed_files()
                listing = "\n".join(f"- `{item['file']}`: +{item['added']} / -{item['removed']} lines" for item in largest)
                return {"ok": True, "kind": "diff_summary", "snapshot": snapshot, "text": f"Largest tracked-file changes:\n{listing or '- No tracked-file diffs.'}", "files": largest}

            summary = snapshot["summary"]
            lines = [
                f"Repository: {snapshot['repository_name']} (`{snapshot['repository_root']}`)",
                f"Branch: `{snapshot['branch']}`",
                f"HEAD: `{snapshot['head_commit']}`",
                "Working tree: " + ("clean" if snapshot["is_clean"] else f"{summary['modified']} modified · {summary['staged']} staged · {summary['untracked']} untracked · {summary['deleted']} deleted · {summary['renamed']} renamed · {summary['conflicted']} conflicted"),
            ]
            entries = snapshot["entries"]
            if entries:
                lines.append("\nChanged files:")
                for entry in entries[:self.MAX_FILES_IN_SUMMARY]:
                    label = " · Potential backup/generated artifact" if self._artifact_warning(entry["path"]) else ""
                    lines.append(f"- `{entry['status']}` {entry['path']}{label}")
                if len(entries) > self.MAX_FILES_IN_SUMMARY:
                    lines.append(f"- … and {snapshot['entry_count'] - self.MAX_FILES_IN_SUMMARY} more")
                elif snapshot.get("files_truncated"):
                    lines.append(f"- … and {snapshot['entry_count'] - len(entries)} more")
            if any(marker in lower for marker in ("recent commits", "last five commits", "five recent", "development state")):
                lines.append("\nRecent commits:\n" + (recent or "- No commits found."))
            if "safe to edit" in lower:
                if snapshot["is_clean"]:
                    lines.append("\nThe working tree is clean. This read-only check doesn't perform or approve edits.")
                else:
                    lines.append("\nThere are existing uncommitted changes. Review and preserve them before editing; this read-only check does not certify them as safe to overwrite.")
            return {"ok": True, "kind": "repository_status", "snapshot": snapshot, "text": "\n".join(lines)}
        except CodeWorkspaceError as exc:
            return {"ok": False, "kind": "error", "text": str(exc)}
        except Exception:
            logger.exception("Code Workspace repository inspection failed")
            return {
                "ok": False,
                "kind": "error",
                "text": "Nova couldn't read the repository right now. Please try again.",
            }
