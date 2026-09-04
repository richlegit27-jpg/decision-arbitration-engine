from __future__ import annotations

import re


def plan_tool_request(
    user_text: str,
):
    original_text = user_text or ""
    text = original_text.lower().strip()

    if not text:
        return {
            "ok": False,
            "tool": None,
            "payload": {},
        }

    # MEMORY DELETE
    if (
        "forget" in text
        or "delete memory" in text
        or "remove memory" in text
    ):
        match = re.search(
            r"memory_[a-zA-Z0-9]+",
            original_text,
        )

        return {
            "ok": True,
            "tool": "memory_delete",
            "payload": {
                "memory_id": match.group(0) if match else "",
            },
        }

    # MEMORY WRITE
    for prefix in [
        "remember that ",
        "remember ",
        "save this ",
        "store this ",
    ]:
        if text.startswith(prefix):
            return {
                "ok": True,
                "tool": "memory_write",
                "payload": {
                    "content": original_text[
                        len(prefix):
                    ].strip(),
                },
            }

    # MEMORY READ
    if any(
        phrase in text
        for phrase in [
            "what do you remember",
            "show my memories",
            "what memories",
            "what do you know about me",
            "list memories",
        ]
    ):
        return {
            "ok": True,
            "tool": "memory_read",
            "payload": {},
        }

    # PROCESS LIST
    if any(
        phrase in text
        for phrase in [
            "list processes",
            "show processes",
            "running processes",
            "what processes are running",
            "show running processes",
            "list running processes",
        ]
    ):
        return {
            "ok": True,
            "tool": "process_list",
            "payload": {},
        }

    # TERMINAL EXECUTE
    for prefix in [
        "run command ",
        "execute command ",
        "run powershell ",
        "execute powershell ",
        "terminal command ",
    ]:
        if text.startswith(prefix):
            command = original_text[
                len(prefix):
            ].strip()

            if command:
                return {
                    "ok": True,
                    "tool": "terminal_execute",
                    "payload": {
                        "command": command,
                    },
                }

    # PROCESS START
    for prefix in [
        "start ",
        "launch ",
        "run program ",
    ]:
        if text.startswith(prefix):
            command = original_text[
                len(prefix):
            ].strip()

            if command:
                return {
                    "ok": True,
                    "tool": "process_start",
                    "payload": {
                        "command": command,
                    },
                }

    # GIT STATUS
    if any(
        phrase in text
        for phrase in [
            "git status",
            "repository status",
            "repo status",
            "what changed in git",
        ]
    ):
        return {
            "ok": True,
            "tool": "git_status",
            "payload": {
                "path": ".",
            },
        }

    # GIT DIFF
    if any(
        phrase in text
        for phrase in [
            "show git diff",
            "git diff",
            "show changes",
            "what are the code changes",
        ]
    ):
        return {
            "ok": True,
            "tool": "git_diff",
            "payload": {
                "path": ".",
            },
        }

    # GIT LOG
    if any(
        phrase in text
        for phrase in [
            "git log",
            "recent commits",
            "show commits",
            "commit history",
        ]
    ):
        return {
            "ok": True,
            "tool": "git_log",
            "payload": {
                "path": ".",
                "limit": 10,
            },
        }

    # GIT SHOW
    if (
        text.startswith("show commit ")
        or text.startswith("git show ")
    ):
        parts = original_text.strip().split()

        return {
            "ok": True,
            "tool": "git_show",
            "payload": {
                "commit": parts[-1] if len(parts) >= 3 else "",
            },
        }

    # GIT COMMIT
    if (
        text.startswith("commit changes ")
        or text.startswith("git commit ")
    ):
        if text.startswith("commit changes "):
            prefix = "commit changes "
        else:
            prefix = "git commit "

        message = original_text[
            len(prefix):
        ].strip()

        if message:
            return {
                "ok": True,
                "tool": "git_commit",
                "payload": {
                    "path": ".",
                    "message": message,
                },
            }

    # CODE SEARCH
    for prefix in [
        "search code for ",
        "find code for ",
        "search the code for ",
        "find in code ",
        "search project for ",
    ]:
        if text.startswith(prefix):
            return {
                "ok": True,
                "tool": "code_search",
                "payload": {
                    "query": original_text[
                        len(prefix):
                    ].strip(),
                },
            }

    # FILE MOVE
    move_match = re.match(
        r"^(?:move|rename)\s+file\s+(.+?)\s+(?:to|as)\s+(.+)$",
        original_text,
        flags=re.IGNORECASE,
    )

    if move_match:
        return {
            "ok": True,
            "tool": "file_move",
            "payload": {
                "source": move_match.group(1).strip(),
                "destination": move_match.group(2).strip(),
            },
        }

    # FILE READ
    for prefix in [
        "read file ",
        "open file ",
        "show file ",
    ]:
        if text.startswith(prefix):
            return {
                "ok": True,
                "tool": "file_read",
                "payload": {
                    "path": original_text[
                        len(prefix):
                    ].strip(),
                },
            }

    # FILE WRITE
    for prefix in [
        "write file ",
        "create file ",
    ]:
        if text.startswith(prefix):
            return {
                "ok": True,
                "tool": "file_write",
                "payload": {
                    "path": original_text[
                        len(prefix):
                    ].strip(),
                    "content": "",
                },
            }

    # FILE LIST
    if any(
        text.startswith(prefix)
        for prefix in [
            "list files",
            "show files",
            "list directory",
            "show directory",
        ]
    ):
        return {
            "ok": True,
            "tool": "file_list",
            "payload": {},
        }

    # FILE DELETE
    for prefix in [
        "delete file ",
        "remove file ",
    ]:
        if text.startswith(prefix):
            return {
                "ok": True,
                "tool": "file_delete",
                "payload": {
                    "path": original_text[
                        len(prefix):
                    ].strip(),
                },
            }

    # DIRECTORY CREATE
    for prefix in [
        "create directory ",
        "create folder ",
        "make directory ",
        "make folder ",
    ]:
        if text.startswith(prefix):
            return {
                "ok": True,
                "tool": "directory_create",
                "payload": {
                    "path": original_text[
                        len(prefix):
                    ].strip(),
                },
            }

    # PROJECT WORKSPACE
    if (
        "update project workspace" in text
        or "update workspace" in text
        or "refresh project workspace" in text
    ):
        return {
            "ok": True,
            "tool": "project_workspace_update",
            "payload": {},
        }

    return {
        "ok": False,
        "tool": None,
        "payload": {},
    }