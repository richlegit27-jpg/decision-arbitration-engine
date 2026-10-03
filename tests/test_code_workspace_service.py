from __future__ import annotations

import subprocess
import tempfile
import shutil
import unittest
import importlib.util
from pathlib import Path

SERVICE_PATH = Path(__file__).resolve().parents[1] / "nova_backend" / "services" / "code_workspace_service.py"
SERVICE_SPEC = importlib.util.spec_from_file_location("nova_code_workspace_service_test", SERVICE_PATH)
SERVICE_MODULE = importlib.util.module_from_spec(SERVICE_SPEC)
SERVICE_SPEC.loader.exec_module(SERVICE_MODULE)
CodeWorkspaceError = SERVICE_MODULE.CodeWorkspaceError
CodeWorkspaceService = SERVICE_MODULE.CodeWorkspaceService
DECISION_PATH = Path(__file__).resolve().parents[1] / "nova_backend" / "services" / "planner" / "decision_service.py"
DECISION_SPEC = importlib.util.spec_from_file_location("nova_decision_service_test", DECISION_PATH)
DECISION_MODULE = importlib.util.module_from_spec(DECISION_SPEC)
DECISION_SPEC.loader.exec_module(DECISION_MODULE)
DecisionService = DECISION_MODULE.DecisionService


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return result.stdout.strip()


def make_repo(parent: Path) -> Path:
    root = parent / "sample-repo"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Test User")
    git(root, "config", "user.email", "test@example.invalid")
    for name, content in {
        "chat_service.py": "def answer():\n    return 'old'\n",
        "delete_me.txt": "remove me\n",
        "rename_me.md": "rename me\n",
        "staged.txt": "stage me\n",
    }.items():
        (root / name).write_text(content, encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "Initial snapshot")
    return root


class CodeWorkspaceServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="nova-code-workspace-")
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_snapshot_reports_repository_and_clean_status(self):
        root = make_repo(self.temp_path)
        before = git(root, "status", "--porcelain=v1")
        snapshot = CodeWorkspaceService(root).snapshot()
        after = git(root, "status", "--porcelain=v1")

        self.assertEqual(snapshot["repository_name"], root.name)
        self.assertEqual(Path(snapshot["repository_root"]), root.resolve())
        self.assertEqual(snapshot["branch"], "main")
        self.assertEqual(len(snapshot["head_commit"]), 40)
        self.assertTrue(snapshot["is_clean"])
        self.assertEqual(before, after)
        self.assertEqual(snapshot["summary"]["modified"], 0)
        self.assertEqual(snapshot["recent_commits"][0]["subject"], "Initial snapshot")


    def test_snapshot_classifies_staged_unstaged_deleted_renamed_and_untracked(self):
        root = make_repo(self.temp_path)
        (root / "chat_service.py").write_text("def answer():\n    return 'new'\n", encoding="utf-8")
        (root / "staged.txt").write_text("staged change\n", encoding="utf-8")
        git(root, "add", "staged.txt")
        (root / "delete_me.txt").unlink()
        git(root, "mv", "rename_me.md", "renamed.md")
        (root / "untracked.log").write_text("generated?\n", encoding="utf-8")

        snapshot = CodeWorkspaceService(root).snapshot()
        self.assertIn("staged.txt", snapshot["staged_files"])
        self.assertIn("chat_service.py", snapshot["unstaged_files"])
        self.assertIn("delete_me.txt", snapshot["deleted_files"])
        self.assertIn("renamed.md", snapshot["renamed_files"])
        self.assertIn("untracked.log", snapshot["untracked_files"])
        self.assertFalse(snapshot["is_clean"])

    def test_snapshot_detects_merge_conflicts(self):
        root = make_repo(self.temp_path)
        (root / "conflict.txt").write_text("base\n", encoding="utf-8")
        git(root, "add", "conflict.txt")
        git(root, "commit", "-m", "Add conflict fixture")
        git(root, "switch", "-c", "side")
        (root / "conflict.txt").write_text("side\n", encoding="utf-8")
        git(root, "commit", "-am", "Side edit")
        git(root, "switch", "main")
        (root / "conflict.txt").write_text("main\n", encoding="utf-8")
        git(root, "commit", "-am", "Main edit")
        merge = subprocess.run(
            ["git", "-C", str(root), "merge", "side"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(merge.returncode, 0)
        snapshot = CodeWorkspaceService(root).snapshot()
        self.assertIn("conflict.txt", snapshot["conflicted_files"])


    def test_invalid_repository_is_rejected(self):
        with self.assertRaisesRegex(CodeWorkspaceError, "Git repository"):
            CodeWorkspaceService(self.temp_path).snapshot()


    def test_file_diff_is_scoped_to_repository_and_redacts_common_secrets(self):
        root = make_repo(self.temp_path)
        (root / "chat_service.py").write_text(
            "def answer():\n    api_key = 'sk-12345678901234567890'\n    return 'new'\n",
            encoding="utf-8",
        )
        service = CodeWorkspaceService(root)
        diff = service.file_diff("chat_service.py")

        self.assertTrue(diff["has_changes"])
        self.assertIn("[REDACTED]", diff["diff"])
        self.assertNotIn("sk-12345678901234567890", diff["diff"])
        with self.assertRaisesRegex(CodeWorkspaceError, "outside"):
            service.file_diff("../outside.txt")
        with self.assertRaisesRegex(CodeWorkspaceError, "credential"):
            service.file_diff(".env")


    def test_diff_truncation_is_reported(self):
        root = make_repo(self.temp_path)
        (root / "chat_service.py").write_text("new value\n" * 200, encoding="utf-8")
        result = CodeWorkspaceService(root, output_limit=300).file_diff("chat_service.py")
        self.assertTrue(result["truncated"])
        self.assertLessEqual(len(result["diff"]), 300)
        self.assertIsNone(result["original_chars"])
        self.assertGreater(result["observed_chars"], result["output_limit"])


    def test_commit_details_and_diff_are_available_by_hash(self):
        root = make_repo(self.temp_path)
        (root / "chat_service.py").write_text("def answer():\n    return 'changed'\n", encoding="utf-8")
        git(root, "add", "chat_service.py")
        git(root, "commit", "-m", "Update answer")
        revision = git(root, "rev-parse", "HEAD")

        service = CodeWorkspaceService(root)
        details = service.commit_details(revision[:10])
        diff = service.commit_diff(revision[:10], "chat_service.py")
        self.assertEqual(details["commit"]["subject"], "Update answer")
        self.assertEqual(details["files"], [{"status": "M", "path": "chat_service.py"}])
        self.assertIn("changed", diff["diff"])
        with self.assertRaisesRegex(CodeWorkspaceError, "commit hash"):
            service.commit_details("--all")

    def test_chat_file_diff_request_uses_configured_repository(self):
        root = make_repo(self.temp_path)
        (root / "chat_service.py").write_text("def answer():\n    return 'new'\n", encoding="utf-8")
        result = CodeWorkspaceService(root).answer_request("What changed in chat_service.py?")
        self.assertTrue(result["ok"])
        self.assertEqual(result["kind"], "file_diff")
        self.assertIn("chat_service.py", result["text"])
        self.assertIn("return 'new'", result["text"])

    def test_component_change_question_uses_changed_paths_as_limited_evidence(self):
        root = make_repo(self.temp_path)
        (root / "execution_service.py").write_text("changed\n", encoding="utf-8")
        result = CodeWorkspaceService(root).answer_request("Did we modify Project Execution?")
        self.assertTrue(result["ok"])
        self.assertEqual(result["kind"], "component_change_check")
        self.assertIn("execution_service.py", result["matching_files"])
        self.assertIn("inspect the file diffs", result["text"])


    def test_read_only_chat_intents_and_mutation_blocking(self):
        service = CodeWorkspaceService()
        self.assertEqual(service.classify_request("What's changed in this repo?"), "read")
        self.assertEqual(service.classify_request("What changed in chat_service.py?"), "read")
        self.assertEqual(service.classify_request("What did we change yesterday?"), "read")
        self.assertEqual(service.classify_request("What happened in commit e92c9fe6?"), "read")
        self.assertIsNone(service.classify_request("Explain photosynthesis"))
        self.assertEqual(service.classify_request("Commit this"), "blocked_mutation")
        self.assertEqual(service.classify_request("git push"), "blocked_mutation")
        self.assertTrue(service.is_git_command_text("git commit -m message"))
        self.assertTrue(service.is_git_command_text("C:\\Program Files\\Git\\cmd\\git.exe status"))
        self.assertFalse(service.answer_request("Commit this")["ok"])
        self.assertIn("read-only", service.answer_request("Commit this")["text"])

        called = []
        no_git_for_mutation = CodeWorkspaceService(
            runner=lambda *args, **kwargs: called.append(args)  # pragma: no cover
        )
        self.assertFalse(no_git_for_mutation.answer_request("Commit this")["ok"])
        self.assertEqual(called, [])

    def test_repository_requests_preempt_pending_execution_without_capturing_normal_chat(self):
        class ChatStub:
            code_workspace_service = CodeWorkspaceService()

            @staticmethod
            def _load_execution_state(_session_id):
                return {"steps": [{"status": "pending"}], "current_index": 0, "status": "running"}

        decisions = DecisionService(ChatStub())
        status = decisions._decide_route("What's changed in this repo?", session_id="test")
        blocked = decisions._decide_route("Commit this", session_id="test")
        self.assertEqual(status["route"], "code_workspace")
        self.assertEqual(status["intent"], "read")
        self.assertEqual(blocked["route"], "code_workspace")
        self.assertEqual(blocked["intent"], "blocked_mutation")


    def test_timeout_returns_safe_actionable_error(self):
        root = make_repo(self.temp_path)

        def timeout_runner(*args, **kwargs):
            raise subprocess.TimeoutExpired(args[0], kwargs.get("timeout"))

        with self.assertRaisesRegex(CodeWorkspaceError, "too long"):
            CodeWorkspaceService(root, runner=timeout_runner).snapshot()


    def test_code_workspace_tool_registry_has_no_mutating_git_tool(self):
        loader_source = (SERVICE_PATH.parents[1] / "tools" / "loader.py").read_text(encoding="utf-8")
        self.assertIn("CodeWorkspaceTool", loader_source)
        self.assertNotIn("GitCommitTool()", loader_source)
        for filename in ("shell_command_tool.py", "terminal_execute_tool.py"):
            tool_source = (SERVICE_PATH.parents[1] / "tools" / filename).read_text(encoding="utf-8")
            self.assertIn("is_git_command_text", tool_source)


if __name__ == "__main__":
    unittest.main()
