from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, Thread
import os
import unittest
from unittest.mock import patch

from nova_backend.services.execution_mutation_service import (
    ExecutionMutationService,
)
from nova_backend.services.execution_approval_service import (
    ExecutionApprovalService,
)
from nova_backend.services.execution_orchestrator_service import (
    ExecutionOrchestratorService,
)
from nova_backend.services.execution_step_service import (
    ExecutionStepService,
)
from nova_backend.services.execution_handler import (
    default_executor,
)
from nova_backend.services.project_execution_controller import (
    ProjectExecutionController,
)
from nova_backend.services.project_builder_service import (
    ProjectBuilderService,
)
from nova_backend.services.project_execution_handler import (
    ProjectExecutionHandler,
)
from nova_backend.services.project_planning_ai_service import (
    ProjectPlanningAIService,
)
from nova_backend.services.project_workspace_service import (
    ProjectWorkspaceService,
)
from nova_backend.services.python_runner_service import (
    PythonRunnerService,
)


class MemoryExecutionStateService:
    def __init__(self):
        self.states = {}

    def get_execution_state(self, session_id):
        return deepcopy(self.states.get(session_id, {}))

    def save_execution_state(self, session_id, execution_state):
        saved = deepcopy(execution_state)
        self.states[session_id] = saved
        return deepcopy(saved)


class ReplacementFailureStepService:
    """Return failure in a new dict without mutating the supplied step."""

    def execute_step_logic(self, session_id, step):
        failed = dict(step)
        failed.update(
            {
                "status": "failed",
                "error": "simulated executor failure",
                "execution_metadata": {
                    "success": False,
                    "error": "simulated executor failure",
                },
            }
        )
        return failed


class RejectingPythonRunner(PythonRunnerService):
    def is_path_allowed(self, file_path):
        return False


class StubChatExecutionService:
    def format_reply(self, execution):
        return ""


class CompletedWrapperOrchestrator:
    """Reproduce a wrapper claiming completion over a failed child step."""

    def __init__(self, failure_step_service, task_id):
        self.execution_state_service = failure_step_service
        self.task_id = task_id

    def process_execution(self, session_id, state, command):
        return {
            "ok": True,
            "execution": {
                "status": "complete",
                "complete": True,
                "steps": [
                    {
                        "id": "failed-child",
                        "task_id": self.task_id,
                        "step_id": "child-step",
                        "status": "failed",
                        "error": "child operation failed",
                    }
                ],
            },
        }


def _build_real_pipeline(tmp_path, step_service=None):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir(parents=True, exist_ok=True)

    workspace = ProjectWorkspaceService(
        data_dir=tmp_path / "project-data"
    )
    execution_state_service = MemoryExecutionStateService()
    approval_service = ExecutionApprovalService()
    step_service = step_service or ExecutionStepService(
        python_runner=PythonRunnerService(sandbox_dir=sandbox),
        approval_service=approval_service,
    )
    orchestrator = ExecutionOrchestratorService(
        execution_state_service=execution_state_service,
        execution_mutation_service=ExecutionMutationService(
            execution_state_service=execution_state_service
        ),
        safe_str=lambda value: str(value or ""),
        execution_step_service=step_service,
        approval_service=approval_service,
        project_workspace_service=workspace,
    )
    controller = ProjectExecutionController(
        project_workspace_service=workspace,
        # The canonical orchestrator is used; this service supplies the
        # controller's existing reply formatter without a legacy execution loop.
        chat_execution_service=StubChatExecutionService(),
        execution_orchestrator_service=orchestrator,
    )
    controller._sandbox_dir = lambda: sandbox
    controller.artifact_publisher.sandbox_dir = sandbox
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    controller.artifact_publisher.uploads_dir = uploads_dir
    return workspace, execution_state_service, orchestrator, controller, sandbox


def _create_project_with_task(workspace, **task_fields):
    project = workspace.create_project(
        title="Execution reliability regression",
        owner_id="regression-test-owner",
    )
    task = workspace.add_task(
        project["id"],
        title="Run execution regression",
        **task_fields,
    )
    assert isinstance(task, dict)
    return project["id"], task["id"]


def _persisted_task(workspace, project_id, task_id):
    project = workspace.get_project(project_id)
    assert isinstance(project, dict)
    return next(
        task
        for task in project.get("tasks", [])
        if isinstance(task, dict) and task.get("id") == task_id
    )


def _mutate_persisted_task(workspace, project_id, task_id, mutate):
    projects = workspace._load_projects()
    project = next(item for item in projects if item.get("id") == project_id)
    task = next(
        item
        for item in project.get("tasks", [])
        if isinstance(item, dict) and item.get("id") == task_id
    )
    mutate(project, task)
    workspace._save_projects(projects)


class TestProjectExecutionReliability(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory(prefix="nova-execution-")
        self.tmp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_execution_step_service_creates_and_modifies_files(self):
        tmp_path = self.tmp_path
        sandbox = tmp_path / "sandbox"
        runner = PythonRunnerService(sandbox_dir=sandbox)
        service = ExecutionStepService(python_runner=runner)

        created = service.execute_step_logic(
            session_id="create-file",
            step={
                "id": "create-file-step",
                "action": "implement",
                "target_file": "sample.py",
                "content": 'VALUE = "created"\n',
            },
        )

        self.assertEqual(created["status"], "completed", created)
        self.assertEqual(
            (sandbox / "sample.py").read_text(encoding="utf-8"),
            'VALUE = "created"\n',
        )

        modified = service.execute_step_logic(
            session_id="modify-file",
            step={
                "id": "modify-file-step",
                "action": "modify",
                "target_file": "sample.py",
                "content": 'VALUE = "modified"\n',
            },
        )

        self.assertEqual(modified["status"], "completed", modified)
        self.assertEqual(
            (sandbox / "sample.py").read_text(encoding="utf-8"),
            'VALUE = "modified"\n',
        )

    def test_project_handler_executes_python_through_step_service(self):
        sandbox = self.tmp_path / "sandbox"
        runner = PythonRunnerService(sandbox_dir=sandbox)
        service = ExecutionStepService(python_runner=runner)
        script = sandbox / "run_this.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text('print("PROJECT_RUN_OK")\n', encoding="utf-8")
        handler = ProjectExecutionHandler(
            default_executor=default_executor,
            execution_step_service=service,
        )

        result = handler.run_next_step(
            action="run_step",
            session_id="project-handler-run",
            execution_state={
                "status": "running",
                "steps": [
                    {
                        "id": "run-script-step",
                        "action": "execute",
                        "title": "Run the script",
                        "execution_file": str(script),
                    }
                ],
                "current_index": 0,
                "complete": False,
                "waiting": False,
            },
        )

        execution = result["execution_state"]
        self.assertIs(result["ok"], True, result)
        self.assertEqual(execution["status"], "complete", execution)
        self.assertEqual(execution["steps"][0]["status"], "completed", execution)
        self.assertIn("PROJECT_RUN_OK", execution["steps"][0]["execution_output"])


    def test_orchestrator_propagates_replacement_failure_result(self):
        state_service = MemoryExecutionStateService()
        orchestrator = ExecutionOrchestratorService(
            execution_state_service=state_service,
            execution_mutation_service=ExecutionMutationService(
                execution_state_service=state_service
            ),
            safe_str=lambda value: str(value or ""),
            execution_step_service=ReplacementFailureStepService(),
        )

        result = orchestrator.process_execution(
            session_id="replacement-failure",
            command="run_all",
            state={
                "goal": "Propagate executor failure",
                "steps": [
                    {
                        "id": "failure-step",
                        "action": "analysis",
                        "title": "Fail without mutating input",
                        "description": "Exercise returned replacement result.",
                    }
                ],
                "current_index": 0,
                "status": "pending",
                "complete": False,
                "waiting": False,
            },
        )

        execution = result["execution"]
        self.assertIs(result["ok"], False, result)
        self.assertEqual(execution["status"], "failed", execution)
        self.assertIs(execution["complete"], False, execution)
        self.assertEqual(execution["steps"][0]["status"], "failed", execution)
        self.assertEqual(
            execution["error"], "simulated executor failure", execution
        )

        persisted = state_service.get_execution_state("replacement-failure")
        self.assertEqual(persisted["status"], "failed", persisted)
        self.assertEqual(persisted["steps"][0]["status"], "failed", persisted)


    def test_controller_persists_failure_when_wrapper_complete_has_failed_step(self):
        tmp_path = self.tmp_path
        workspace, state_service, _orchestrator, controller, _sandbox = (
            _build_real_pipeline(tmp_path)
        )
        project_id, task_id = _create_project_with_task(
            workspace,
            action="implement",
            description="A wrapper will return a failed child step.",
            target_file="will_not_be_materialized.txt",
            content="The wrapper controls this result.",
            steps=[
                {
                    "id": "child-step",
                    "title": "Child operation",
                    "action": "implement",
                    "status": "pending",
                }
            ],
        )
        controller.execution_orchestrator_service = CompletedWrapperOrchestrator(
            state_service,
            task_id,
        )

        result = controller.run_all(project_id)

        self.assertIs(result["ok"], False, result)
        self.assertEqual(result["status"], "failed", result)
        persisted_project = workspace.get_project(project_id)
        persisted_task = next(
            task for task in persisted_project["tasks"] if task["id"] == task_id
        )
        self.assertEqual(persisted_task["status"], "failed", persisted_task)
        self.assertEqual(
            persisted_task["steps"][0]["status"],
            "failed",
            persisted_task,
        )

    def test_full_project_pipeline_persists_executor_failure(self):
        tmp_path = self.tmp_path
        sandbox = tmp_path / "sandbox"
        rejecting_step_service = ExecutionStepService(
            python_runner=RejectingPythonRunner(sandbox_dir=sandbox)
        )
        workspace, _state_service, _orchestrator, controller, _sandbox = (
            _build_real_pipeline(
                tmp_path,
                step_service=rejecting_step_service,
            )
        )
        project_id, task_id = _create_project_with_task(
            workspace,
            action="implement",
            description="The executor returns a replacement failure result.",
            target_file="../outside/failed_output.txt",
            content="This content must not be treated as success.",
        )

        result = controller.run_all(project_id)

        self.assertIs(result["ok"], False, result)
        self.assertEqual(result["status"], "failed", result)
        persisted_project = workspace.get_project(project_id)
        persisted_task = next(
            task for task in persisted_project["tasks"] if task["id"] == task_id
        )
        self.assertEqual(persisted_task["status"], "failed", persisted_task)
        self.assertEqual(
            workspace.get_execution_state(project_id)["status"],
            result["status"],
        )
        self.assertEqual(persisted_project["status"], "failed")


    def test_controller_runs_real_file_write_and_persists_completion(self):
        tmp_path = self.tmp_path
        workspace, _state_service, _orchestrator, controller, sandbox = (
            _build_real_pipeline(tmp_path)
        )
        project_id, task_id = _create_project_with_task(
            workspace,
            action="implement",
            description="Create a file through the execution step service.",
            target_file="created_by_project.py",
            content='VALUE = "from-project-executor"\n',
        )

        result = controller.run_all(project_id)

        self.assertIs(result["ok"], True, result)
        self.assertEqual(result["status"], "completed", result)
        self.assertEqual(
            (sandbox / "created_by_project.py").read_text(encoding="utf-8"),
            'VALUE = "from-project-executor"\n',
        )

        persisted_project = workspace.get_project(project_id)
        persisted_task = next(
            task for task in persisted_project["tasks"] if task["id"] == task_id
        )
        self.assertEqual(persisted_task["status"], "completed", persisted_task)
        self.assertEqual(
            workspace.get_execution_state(project_id)["status"],
            result["status"],
        )
        self.assertEqual(persisted_project["status"], "completed")

    def test_persisted_parent_completion_does_not_hide_unfinished_step(self):
        workspace, _state_service, _orchestrator, _controller, _sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project_id, task_id = _create_project_with_task(
            workspace,
            action="implement",
            description="A completed parent still has an unfinished child.",
            target_file="pending_child.txt",
            content="This task must not become a false success.",
            steps=[
                {
                    "id": "pending-child",
                    "title": "Pending child",
                    "action": "implement",
                    "status": "pending",
                }
            ],
        )

        projects = workspace._load_projects()
        project = next(item for item in projects if item["id"] == project_id)
        task = next(item for item in project["tasks"] if item["id"] == task_id)
        task["status"] = "completed"
        workspace._save_projects(projects)

        persisted_project = workspace.get_project(project_id)
        persisted_task = next(
            task for task in persisted_project["tasks"] if task["id"] == task_id
        )
        self.assertEqual(persisted_task["status"], "blocked", persisted_task)
        self.assertEqual(
            persisted_task["steps"][0]["status"],
            "pending",
            persisted_task,
        )

    def test_next_aliases_advance_exactly_one_task(self):
        for alias in ("next", "next_task", "next_step"):
            with self.subTest(alias=alias):
                base_path = self.tmp_path / alias
                workspace, _state, _orchestrator, controller, sandbox = (
                    _build_real_pipeline(base_path)
                )
                project = workspace.create_project(
                    title=f"Next alias {alias}",
                    owner_id="regression-test-owner",
                )
                first = workspace.add_task(
                    project["id"],
                    title="First task",
                    action="implement",
                    target_file=f"{alias}-first.txt",
                    content="first",
                )
                second = workspace.add_task(
                    project["id"],
                    title="Second task",
                    action="implement",
                    target_file=f"{alias}-second.txt",
                    content="second",
                )

                result = controller.control(project["id"], alias)

                self.assertIs(result["ok"], True, result)
                self.assertEqual(result["status"], "ready", result)
                self.assertEqual(
                    _persisted_task(
                        workspace, project["id"], first["id"]
                    )["status"],
                    "completed",
                )
                self.assertEqual(
                    _persisted_task(
                        workspace, project["id"], second["id"]
                    )["status"],
                    "open",
                )
                self.assertTrue((sandbox / f"{alias}-first.txt").is_file())
                self.assertFalse((sandbox / f"{alias}-second.txt").exists())

    def test_run_all_honors_dependencies_and_persists_completion(self):
        workspace, _state, _orchestrator, controller, sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project = workspace.create_project(
            title="Dependency order",
            owner_id="regression-test-owner",
        )
        first = workspace.add_task(
            project["id"],
            title="Create dependency",
            action="implement",
            target_file="dependency.txt",
            content="dependency-ready",
        )
        second = workspace.add_task(
            project["id"],
            title="Create dependent output",
            action="implement",
            dependencies=[first["id"]],
            target_file="dependent.txt",
            content="dependent-ready",
        )

        result = controller.run_all(project["id"])

        self.assertIs(result["ok"], True, result)
        self.assertEqual(result["status"], "completed", result)
        persisted = workspace.get_project(project["id"])
        persisted_statuses = {
            task["id"]: task["status"] for task in persisted["tasks"]
        }
        self.assertEqual(persisted_statuses[first["id"]], "completed")
        self.assertEqual(persisted_statuses[second["id"]], "completed")
        self.assertEqual(persisted["status"], "completed")
        self.assertEqual(
            workspace.get_execution_state(project["id"])["status"],
            "completed",
        )
        self.assertEqual(
            (sandbox / "dependency.txt").read_text(encoding="utf-8"),
            "dependency-ready",
        )
        self.assertEqual(
            (sandbox / "dependent.txt").read_text(encoding="utf-8"),
            "dependent-ready",
        )

    def test_missing_target_or_executable_input_is_blocked_and_persisted(self):
        cases = (
            ("implement", "target file"),
            ("execute", "execution_file"),
            ("command", "command"),
        )
        for action, expected_detail in cases:
            with self.subTest(action=action):
                workspace, _state, _orchestrator, controller, _sandbox = (
                    _build_real_pipeline(self.tmp_path / action)
                )
                project_id, task_id = _create_project_with_task(
                    workspace,
                    action=action,
                    description=(
                        "The planner supplied an action but omitted its "
                        "required executable input."
                    ),
                )

                result = controller.run_all(project_id)

                self.assertIs(result["ok"], False, result)
                self.assertEqual(result["status"], "blocked", result)
                persisted_task = _persisted_task(
                    workspace, project_id, task_id
                )
                self.assertEqual(
                    persisted_task["status"], "blocked", persisted_task
                )
                if action == "implement":
                    self.assertEqual(persisted_task.get("target_file"), "")
                    self.assertEqual(persisted_task.get("target_files"), [])
                self.assertIn(
                    expected_detail,
                    str(persisted_task.get("error") or ""),
                )
                self.assertEqual(
                    workspace.get_execution_state(project_id)["status"],
                    "blocked",
                )

    def test_duplicate_run_all_and_next_requests_return_busy(self):
        workspace, _state, _orchestrator, controller, _sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project_id, task_id = _create_project_with_task(
            workspace,
            action="implement",
            target_file="busy.txt",
            content="busy",
        )
        entered = Event()
        release = Event()
        thread_result = {}

        def blocking_execution(**_kwargs):
            entered.set()
            if not release.wait(timeout=5):
                raise TimeoutError("busy-lock test timed out")
            return {
                "ok": True,
                "execution": {
                    "status": "running",
                    "complete": False,
                    "waiting": False,
                    "steps": [
                        {
                            "id": "busy-step",
                            "task_id": task_id,
                            "status": "pending",
                        }
                    ],
                },
            }

        controller._execute_with_existing_orchestrator = blocking_execution

        def run_first_request():
            try:
                thread_result["result"] = controller.run_all(project_id)
            except BaseException as exc:  # surfaced in the main test thread
                thread_result["error"] = exc

        worker = Thread(target=run_first_request, daemon=True)
        worker.start()
        try:
            self.assertTrue(entered.wait(timeout=5))
            duplicate_run_all = controller.run_all(project_id)
            duplicate_next = controller.control(project_id, "next_task")
            for duplicate in (duplicate_run_all, duplicate_next):
                self.assertIs(duplicate["ok"], False, duplicate)
                self.assertEqual(duplicate["status"], "busy", duplicate)
                self.assertIn("run_all", duplicate["message"])
        finally:
            release.set()
            worker.join(timeout=5)

        self.assertFalse(worker.is_alive())
        self.assertNotIn("error", thread_result, thread_result)

    def test_project_lock_is_released_when_execution_raises(self):
        workspace, _state, _orchestrator, controller, _sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project_id, _task_id = _create_project_with_task(
            workspace,
            action="implement",
            target_file="after-exception.txt",
            content="lock-released",
        )
        real_execute = controller._execute_with_existing_orchestrator

        def raise_from_executor(**_kwargs):
            raise RuntimeError("simulated controller execution exception")

        controller._execute_with_existing_orchestrator = raise_from_executor
        try:
            with self.assertRaisesRegex(
                RuntimeError, "simulated controller execution exception"
            ):
                controller.continue_project(project_id)
        finally:
            controller._execute_with_existing_orchestrator = real_execute

        retried = controller.control(project_id, "next_task")
        self.assertNotEqual(retried.get("status"), "busy", retried)
        self.assertEqual(retried["status"], "completed", retried)

    def test_run_all_stops_when_execution_makes_no_progress(self):
        workspace, _state, _orchestrator, controller, _sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project_id, task_id = _create_project_with_task(
            workspace,
            action="implement",
            target_file="no-progress.txt",
            content="pending forever",
        )

        def no_progress_execution(**_kwargs):
            return {
                "ok": True,
                "execution": {
                    "status": "running",
                    "complete": False,
                    "waiting": False,
                    "steps": [
                        {
                            "id": "no-progress-step",
                            "task_id": task_id,
                            "status": "pending",
                        }
                    ],
                },
            }

        controller._execute_with_existing_orchestrator = no_progress_execution

        result = controller.run_all(project_id)

        self.assertIs(result["ok"], False, result)
        self.assertEqual(result["status"], "blocked", result)
        self.assertIn("no progress", result["message"].lower())
        persisted_task = _persisted_task(workspace, project_id, task_id)
        self.assertEqual(persisted_task["status"], "blocked")
        self.assertIn("no progress", persisted_task["error"].lower())
        self.assertEqual(
            workspace.get_execution_state(project_id)["status"],
            "blocked",
        )

    def test_pause_then_resume_runs_the_pending_task(self):
        workspace, _state, _orchestrator, controller, sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project_id, task_id = _create_project_with_task(
            workspace,
            action="implement",
            target_file="resumed.txt",
            content="resumed",
        )

        paused = controller.control(project_id, "pause")

        self.assertEqual(paused["status"], "paused", paused)
        self.assertEqual(
            workspace.get_execution_state(project_id)["control_request"],
            "pause",
        )
        self.assertEqual(workspace.get_project(project_id)["status"], "paused")

        resumed = controller.control(project_id, "resume")

        self.assertIs(resumed["ok"], True, resumed)
        self.assertEqual(resumed["status"], "completed", resumed)
        self.assertEqual(
            _persisted_task(workspace, project_id, task_id)["status"],
            "completed",
        )
        resumed_state = workspace.get_execution_state(project_id)
        self.assertEqual(resumed_state["status"], "completed")
        self.assertIsNone(resumed_state["control_request"])
        self.assertEqual(
            (sandbox / "resumed.txt").read_text(encoding="utf-8"),
            "resumed",
        )

    def test_reset_clears_terminal_state_and_allows_run_all_reexecution(self):
        workspace, _state, _orchestrator, controller, _sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project_id, task_id = _create_project_with_task(
            workspace,
            action="implement",
            steps=[
                {
                    "id": "reset-child",
                    "action": "implement",
                    "target_file": "reset-output.txt",
                    "content": "resettable",
                    "status": "pending",
                }
            ],
        )
        completed = controller.run_all(project_id)
        self.assertEqual(completed["status"], "completed", completed)

        reset = controller.control(project_id, "reset")

        self.assertIs(reset["ok"], True, reset)
        self.assertEqual(reset["status"], "ready", reset)
        persisted_task = _persisted_task(workspace, project_id, task_id)
        self.assertEqual(persisted_task["status"], "open", persisted_task)
        self.assertEqual(
            persisted_task["steps"][0]["status"], "pending", persisted_task
        )
        self.assertEqual(
            workspace.get_execution_state(project_id)["status"], "ready"
        )

        rerun = controller.run_all(project_id)
        self.assertEqual(rerun["status"], "completed", rerun)
        self.assertEqual(
            _persisted_task(workspace, project_id, task_id)["status"],
            "completed",
        )

    def test_dependency_cycle_is_blocked_with_persisted_blockers(self):
        workspace, _state, _orchestrator, controller, _sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project = workspace.create_project(
            title="Dependency cycle",
            owner_id="regression-test-owner",
        )
        first = workspace.add_task(
            project["id"],
            title="Cycle task A",
            action="implement",
            dependencies=["Cycle task B"],
            target_file="cycle-a.txt",
            content="a",
        )
        second = workspace.add_task(
            project["id"],
            title="Cycle task B",
            action="implement",
            dependencies=["Cycle task A"],
            target_file="cycle-b.txt",
            content="b",
        )

        result = controller.run_all(project["id"])

        self.assertIs(result["ok"], False, result)
        self.assertEqual(result["status"], "blocked", result)
        for task_id in (first["id"], second["id"]):
            persisted_task = _persisted_task(
                workspace, project["id"], task_id
            )
            self.assertEqual(persisted_task["status"], "blocked")
            self.assertIn("cyclic", persisted_task["error"].lower())
        self.assertEqual(
            workspace.get_execution_state(project["id"])["status"],
            "blocked",
        )

    def test_orchestrator_cancel_is_persisted(self):
        state_service = MemoryExecutionStateService()
        orchestrator = ExecutionOrchestratorService(
            execution_state_service=state_service,
            execution_mutation_service=ExecutionMutationService(
                execution_state_service=state_service
            ),
            safe_str=lambda value: str(value or ""),
            execution_step_service=ExecutionStepService(
                python_runner=PythonRunnerService(
                    sandbox_dir=self.tmp_path / "sandbox"
                )
            ),
        )

        result = orchestrator.process_execution(
            session_id="cancel-regression",
            command="cancel",
            state={
                "status": "running",
                "complete": False,
                "waiting": False,
                "current_index": 0,
                "steps": [
                    {
                        "id": "cancel-step",
                        "action": "implement",
                        "target_file": "cancelled.txt",
                        "content": "must not run",
                        "status": "pending",
                    }
                ],
            },
        )

        self.assertIs(result["ok"], True, result)
        self.assertEqual(result["execution"]["status"], "cancelled")
        self.assertIs(result["execution"]["complete"], False)
        persisted = state_service.get_execution_state("cancel-regression")
        self.assertEqual(persisted["status"], "cancelled", persisted)
        self.assertEqual(persisted["steps"][0]["status"], "pending")

    def test_required_approval_waits_without_reporting_completion(self):
        workspace, _state, _orchestrator, controller, sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        script = sandbox / "approval.py"
        script.write_text('print("APPROVED")\n', encoding="utf-8")
        project_id, task_id = _create_project_with_task(
            workspace,
            action="execute",
            execution_file=str(script),
            requires_approval=True,
        )

        result = controller.run_all(project_id)

        self.assertIs(result["ok"], True, result)
        self.assertEqual(result["status"], "waiting_approval", result)
        persisted_state = workspace.get_execution_state(project_id)
        self.assertEqual(persisted_state["status"], "waiting_approval")
        self.assertEqual(persisted_state["current_task_id"], task_id)
        persisted_task = _persisted_task(workspace, project_id, task_id)
        self.assertNotEqual(persisted_task["status"], "completed")
        self.assertNotEqual(workspace.get_project(project_id)["status"], "completed")

    def test_failed_result_without_execution_payload_fails_current_task(self):
        workspace, _state, _orchestrator, controller, _sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project_id, task_id = _create_project_with_task(
            workspace,
            action="implement",
            target_file="bare-failure.txt",
            content="must remain failed",
        )

        controller._execute_with_existing_orchestrator = lambda **_kwargs: {
            "ok": False,
            "status": "failed",
            "error": "bare executor failure",
        }

        result = controller.run_all(project_id)

        self.assertIs(result["ok"], False, result)
        self.assertEqual(result["status"], "failed", result)
        persisted_task = _persisted_task(workspace, project_id, task_id)
        self.assertEqual(persisted_task["status"], "failed", persisted_task)
        self.assertEqual(persisted_task["error"], "bare executor failure")
        self.assertEqual(
            workspace.get_execution_state(project_id)["status"], "failed"
        )
        self.assertEqual(workspace.get_project(project_id)["status"], "failed")

    def test_task_level_approval_blocks_writes_and_reset_requires_approval_again(self):
        workspace, _state, _orchestrator, controller, sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project_id, task_id = _create_project_with_task(
            workspace,
            action="implement",
            target_file="protected-write.txt",
            content="approved content",
            requires_approval=True,
        )
        protected_file = sandbox / "protected-write.txt"

        waiting = controller.continue_project(project_id)

        self.assertEqual(waiting["status"], "waiting_approval", waiting)
        self.assertFalse(protected_file.exists())

        approved = controller.approve_project(project_id)

        self.assertIs(approved["ok"], True, approved)
        self.assertEqual(approved["status"], "completed", approved)
        self.assertEqual(
            protected_file.read_text(encoding="utf-8"),
            "approved content",
        )

        controller.reset_execution_state(project_id)
        protected_file.unlink()
        reset_task = _persisted_task(workspace, project_id, task_id)
        self.assertIs(reset_task["approval_required"], True, reset_task)
        self.assertIs(reset_task["requires_approval"], True, reset_task)
        self.assertNotIn("approved", reset_task)

        waiting_again = controller.run_all(project_id)

        self.assertEqual(
            waiting_again["status"], "waiting_approval", waiting_again
        )
        self.assertFalse(protected_file.exists())

    def test_terminal_execution_cannot_be_overwritten_by_pause_or_stop(self):
        workspace, _state, _orchestrator, controller, _sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        completed_project, _completed_task = _create_project_with_task(
            workspace,
            action="implement",
            target_file="terminal-complete.txt",
            content="complete",
        )
        self.assertEqual(controller.run_all(completed_project)["status"], "completed")

        pause_result = controller.pause_project(completed_project)

        self.assertIs(pause_result["ok"], False, pause_result)
        self.assertEqual(pause_result["status"], "completed", pause_result)
        self.assertEqual(
            workspace.get_execution_state(completed_project)["status"],
            "completed",
        )

        failed_project, failed_task = _create_project_with_task(
            workspace,
            action="implement",
            content="missing target",
        )
        failure = controller.continue_project(failed_project)
        self.assertEqual(failure["status"], "blocked", failure)

        stop_result = controller.stop_project(failed_project)

        self.assertIs(stop_result["ok"], False, stop_result)
        self.assertEqual(stop_result["status"], "blocked", stop_result)
        self.assertEqual(
            _persisted_task(workspace, failed_project, failed_task)["status"],
            "blocked",
        )
        self.assertEqual(
            workspace.get_execution_state(failed_project)["status"],
            "blocked",
        )

    def test_idless_nested_step_gets_a_stable_persisted_identity(self):
        workspace, _state, _orchestrator, controller, sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project_id, task_id = _create_project_with_task(
            workspace,
            steps=[
                {
                    "title": "Write an idless child",
                    "action": "implement",
                    "target_file": "idless-child.txt",
                    "content": "stable identity",
                }
            ],
        )
        before = _persisted_task(workspace, project_id, task_id)
        persisted_id = before["steps"][0].get("id")
        self.assertTrue(persisted_id, before)

        result = controller.run_all(project_id)

        self.assertEqual(result["status"], "completed", result)
        after = _persisted_task(workspace, project_id, task_id)
        self.assertEqual(after["steps"][0]["id"], persisted_id, after)
        self.assertEqual(after["steps"][0]["status"], "completed", after)
        self.assertEqual(
            (sandbox / "idless-child.txt").read_text(encoding="utf-8").strip(),
            "stable identity",
        )

    def test_planner_contract_preserves_non_file_steps_without_inventing_targets(self):
        service = ProjectPlanningAIService()
        plan = service._normalize_plan(
            {
                "name": "Planner contract",
                "tasks": [
                    {
                        "title": "Execute the supplied steps",
                        "action": "implement",
                        "steps": [
                            {
                                "title": "Needs a target from the user",
                                "action": "analyze",
                                "payload": {"key": "value"},
                                "approval_required": True,
                            },
                            {
                                "title": "Run the supplied script",
                                "action": "run",
                                "execution_file": "verify.py",
                            },
                        ],
                    }
                ],
            },
            "Implement the supplied plan",
        )

        steps = plan["tasks"][0]["steps"]
        self.assertEqual(len(steps), 2, steps)
        self.assertEqual(steps[0]["target_file"], "")
        self.assertEqual(steps[0]["target_files"], [])
        self.assertEqual(steps[0]["payload"], {"key": "value"})
        self.assertIs(steps[0]["approval_required"], True)
        self.assertEqual(steps[1]["execution_file"], "verify.py")

    def test_planner_rejects_file_mutation_without_authoritative_target(self):
        service = ProjectPlanningAIService()
        with self.assertRaisesRegex(
            ValueError,
            "file operation without a target_file.*target_files",
        ):
            service._normalize_plan(
                {
                    "name": "AI Video Creation",
                    "tasks": [
                        {
                            "title": "Implement the video assembly and export process",
                            "action": "implement",
                            "execution_mode": "ai",
                            "expected_output": (
                                "A rendered video file in a standard output format."
                            ),
                            "steps": [
                                {
                                    "id": "step-2",
                                    "title": "Add export and render support",
                                    "description": (
                                        "Implement final rendering to a common "
                                        "video format suitable for playback and sharing."
                                    ),
                                    "action": "implement",
                                    "expected_output": (
                                        "A rendered video file in a standard output format."
                                    ),
                                }
                            ],
                        }
                    ],
                },
                "i want to make an ai video",
            )

    def test_planned_file_target_survives_build_persistence_and_execution(self):
        workspace, _state, _orchestrator, controller, sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        planning_service = ProjectPlanningAIService()
        plan = planning_service._normalize_plan(
            {
                "name": "Export module",
                "tasks": [
                    {
                        "title": "Create the video export module",
                        "action": "implement",
                        "execution_mode": "hybrid",
                        "target_file": "video_export.py",
                        "steps": [
                            {
                                "id": "write-export-module",
                                "title": "Write the export module",
                                "action": "implement",
                                "target_file": "video_export.py",
                                "content": 'OUTPUT_FORMAT = "mp4"',
                            }
                        ],
                    }
                ],
            },
            "Create a video export module",
        )
        builder = ProjectBuilderService(workspace)
        builder._build_project_plan = lambda request, project_context=None: plan

        result = builder.build_project_from_request(
            "Create a video export module"
        )
        project_id = result["project_id"]
        task_id = result["tasks"][0]["id"]
        persisted_task = _persisted_task(workspace, project_id, task_id)
        self.assertEqual(persisted_task["target_file"], "video_export.py")
        self.assertEqual(
            persisted_task["steps"][0]["target_file"], "video_export.py"
        )

        execution = controller.run_all(project_id)

        self.assertTrue(execution["ok"], execution)
        self.assertEqual(execution["status"], "completed", execution)
        self.assertEqual(
            (sandbox / "video_export.py").read_text(encoding="utf-8"),
            'OUTPUT_FORMAT = "mp4"',
        )
        persisted_task = _persisted_task(workspace, project_id, task_id)
        self.assertEqual(persisted_task["status"], "completed", persisted_task)
        self.assertEqual(
            persisted_task["steps"][0]["status"], "completed", persisted_task
        )

    def test_default_python_runner_uses_configured_isolated_sandbox(self):
        configured_sandbox = self.tmp_path / "configured-sandbox"

        with patch.dict(
            os.environ,
            {"NOVA_EXECUTION_SANDBOX_DIR": str(configured_sandbox)},
        ):
            runner = PythonRunnerService()

        self.assertEqual(runner.sandbox_dir, configured_sandbox.resolve())
        self.assertTrue(configured_sandbox.is_dir())

    def test_pause_arriving_with_final_completion_stays_completed(self):
        workspace, _state, _orchestrator, controller, _sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project_id, task_id = _create_project_with_task(
            workspace,
            action="implement",
            target_file="pause-at-finish.txt",
            content="finished",
        )

        def finish_after_pause(**_kwargs):
            controller.pause_project(project_id)
            return {
                "ok": True,
                "execution": {
                    "status": "complete",
                    "complete": True,
                    "waiting": False,
                    "steps": [
                        {
                            "id": "pause-at-finish-step",
                            "task_id": task_id,
                            "status": "completed",
                            "result": "finished",
                        }
                    ],
                },
            }

        controller._execute_with_existing_orchestrator = finish_after_pause

        result = controller.run_all(project_id)

        self.assertIs(result["ok"], True, result)
        self.assertEqual(result["status"], "completed", result)
        persisted_state = workspace.get_execution_state(project_id)
        self.assertEqual(persisted_state["status"], "completed")
        self.assertIsNone(persisted_state["control_request"])
        self.assertEqual(
            _persisted_task(workspace, project_id, task_id)["status"],
            "completed",
        )
        self.assertEqual(workspace.get_project(project_id)["status"], "completed")

    def test_pause_arriving_with_step_failure_preserves_failure(self):
        workspace, _state, _orchestrator, controller, _sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project_id, task_id = _create_project_with_task(
            workspace,
            action="implement",
            target_file="pause-and-fail.txt",
            content="must fail",
        )

        def fail_after_pause(**_kwargs):
            controller.pause_project(project_id)
            return {
                "ok": False,
                "execution": {
                    "status": "failed",
                    "complete": False,
                    "waiting": False,
                    "error": "failure won over pause",
                    "steps": [
                        {
                            "id": "pause-failure-step",
                            "task_id": task_id,
                            "status": "failed",
                            "error": "failure won over pause",
                        }
                    ],
                },
            }

        controller._execute_with_existing_orchestrator = fail_after_pause

        result = controller.continue_project(project_id)

        self.assertIs(result["ok"], False, result)
        self.assertEqual(result["status"], "failed", result)
        persisted_task = _persisted_task(workspace, project_id, task_id)
        self.assertEqual(persisted_task["status"], "failed", persisted_task)
        self.assertEqual(persisted_task["error"], "failure won over pause")
        self.assertEqual(
            workspace.get_execution_state(project_id)["status"], "failed"
        )
        self.assertEqual(workspace.get_project(project_id)["status"], "failed")

    def test_pause_during_two_task_run_all_stops_then_resume_completes(self):
        workspace, _state, _orchestrator, controller, sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project = workspace.create_project(
            title="Pause partial Run All",
            owner_id="regression-test-owner",
        )
        first = workspace.add_task(
            project["id"],
            title="First before pause",
            action="implement",
            target_file="pause-first.txt",
            content="first",
        )
        second = workspace.add_task(
            project["id"],
            title="Second after resume",
            action="implement",
            dependencies=[first["id"]],
            target_file="pause-second.txt",
            content="second",
        )
        real_execute = controller._execute_with_existing_orchestrator
        execution_calls = []

        def complete_first_after_pause(**_kwargs):
            execution_calls.append(first["id"])
            controller.pause_project(project["id"])
            return {
                "ok": True,
                "execution": {
                    "status": "complete",
                    "complete": True,
                    "waiting": False,
                    "steps": [
                        {
                            "id": "partial-pause-step",
                            "task_id": first["id"],
                            "status": "completed",
                            "result": "first completed",
                        }
                    ],
                },
            }

        controller._execute_with_existing_orchestrator = (
            complete_first_after_pause
        )
        try:
            paused = controller.run_all(project["id"])
        finally:
            controller._execute_with_existing_orchestrator = real_execute

        self.assertIs(paused["ok"], False, paused)
        self.assertEqual(paused["status"], "paused", paused)
        self.assertEqual(execution_calls, [first["id"]])
        self.assertEqual(
            _persisted_task(workspace, project["id"], first["id"])["status"],
            "completed",
        )
        self.assertEqual(
            _persisted_task(workspace, project["id"], second["id"])["status"],
            "open",
        )
        self.assertFalse((sandbox / "pause-second.txt").exists())

        resumed = controller.control(project["id"], "resume")

        self.assertIs(resumed["ok"], True, resumed)
        self.assertEqual(resumed["status"], "completed", resumed)
        self.assertEqual(
            _persisted_task(workspace, project["id"], second["id"])["status"],
            "completed",
        )
        self.assertEqual(
            workspace.get_execution_state(project["id"])["status"],
            "completed",
        )
        self.assertEqual(
            (sandbox / "pause-second.txt").read_text(encoding="utf-8"),
            "second",
        )

    def test_unknown_project_next_returns_not_found_signal(self):
        _workspace, _state, _orchestrator, controller, _sandbox = (
            _build_real_pipeline(self.tmp_path)
        )

        result = controller.control("missing-project", "next")

        self.assertIsNone(result)

    def test_invalid_control_action_is_rejected_without_mutation(self):
        workspace, _state, _orchestrator, controller, _sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project_id, task_id = _create_project_with_task(
            workspace,
            action="implement",
            target_file="invalid-action.txt",
            content="untouched",
        )
        before_state = deepcopy(workspace.get_execution_state(project_id))

        result = controller.control(project_id, "launch_everything")

        self.assertIs(result["ok"], False, result)
        self.assertEqual(result["status"], "invalid_action", result)
        self.assertEqual(
            _persisted_task(workspace, project_id, task_id)["status"], "open"
        )
        self.assertEqual(workspace.get_execution_state(project_id), before_state)

    def test_next_respects_dependency_order_across_calls(self):
        workspace, _state, _orchestrator, controller, sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project = workspace.create_project(
            title="Next dependency order",
            owner_id="regression-test-owner",
        )
        first = workspace.add_task(
            project["id"],
            title="Next prerequisite",
            action="implement",
            target_file="next-prerequisite.txt",
            content="first",
        )
        second = workspace.add_task(
            project["id"],
            title="Next dependent",
            action="implement",
            dependencies=[first["id"]],
            target_file="next-dependent.txt",
            content="second",
        )

        first_result = controller.control(project["id"], "next_task")

        self.assertEqual(first_result["status"], "ready", first_result)
        self.assertEqual(
            _persisted_task(workspace, project["id"], first["id"])["status"],
            "completed",
        )
        self.assertEqual(
            _persisted_task(workspace, project["id"], second["id"])["status"],
            "open",
        )
        self.assertFalse((sandbox / "next-dependent.txt").exists())

        second_result = controller.control(project["id"], "next_task")

        self.assertEqual(second_result["status"], "completed", second_result)
        self.assertEqual(
            _persisted_task(workspace, project["id"], second["id"])["status"],
            "completed",
        )
        self.assertEqual(
            (sandbox / "next-dependent.txt").read_text(encoding="utf-8"),
            "second",
        )

    def test_run_all_with_no_work_returns_persisted_completion(self):
        workspace, _state, _orchestrator, controller, _sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project = workspace.create_project(
            title="No work",
            owner_id="regression-test-owner",
        )

        result = controller.run_all(project["id"])

        self.assertIs(result["ok"], True, result)
        self.assertEqual(result["status"], "completed", result)
        self.assertIn("no executable work", result["message"].lower())
        self.assertEqual(
            workspace.get_execution_state(project["id"])["status"],
            "completed",
        )

    def test_continue_cancellation_is_persisted_at_every_layer(self):
        workspace, _state, _orchestrator, controller, _sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project_id, task_id = _create_project_with_task(
            workspace,
            action="implement",
            target_file="cancel-continue.txt",
            content="cancelled",
        )

        controller._execute_with_existing_orchestrator = lambda **_kwargs: {
            "ok": True,
            "execution": {
                "status": "cancelled",
                "complete": False,
                "waiting": False,
                "error": "cancelled by regression test",
                "steps": [
                    {
                        "id": "cancelled-child",
                        "task_id": task_id,
                        "status": "cancelled",
                        "error": "cancelled by regression test",
                    }
                ],
            },
        }

        result = controller.continue_project(project_id)

        self.assertIs(result["ok"], False, result)
        self.assertEqual(result["status"], "cancelled", result)
        self.assertEqual(result["execution_status"], "cancelled", result)
        self.assertEqual(result["execution"]["status"], "cancelled")
        persisted_task = _persisted_task(workspace, project_id, task_id)
        self.assertEqual(persisted_task["status"], "cancelled", persisted_task)
        self.assertEqual(
            persisted_task["error"], "cancelled by regression test"
        )
        self.assertEqual(
            workspace.get_execution_state(project_id)["status"], "cancelled"
        )
        self.assertEqual(
            workspace.get_project(project_id)["status"], "cancelled"
        )

    def test_reset_clears_failures_for_all_step_aliases_and_keeps_active_project(self):
        workspace, _state, _orchestrator, controller, _sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project_id, task_id = _create_project_with_task(
            workspace,
            action="implement",
            target_file="reset-aliases.txt",
            content="reset aliases",
        )

        def seed_failed_state(project, task):
            project["active"] = True
            project["status"] = "failed"
            project["execution"]["status"] = "failed"
            task["status"] = "failed"
            task["error"] = "stale task failure"
            for container_name in ("steps", "substeps", "execution_steps"):
                task[container_name] = [
                    {
                        "id": f"{container_name}-child",
                        "action": "implement",
                        "target_file": f"{container_name}.txt",
                        "content": container_name,
                        "status": "failed",
                        "state": "failed",
                        "completion_status": "failed",
                        "error": f"stale {container_name} failure",
                        "result": "stale result",
                        "retry_count": 3,
                    }
                ]

        _mutate_persisted_task(
            workspace, project_id, task_id, seed_failed_state
        )

        result = controller.reset_execution_state(project_id)

        self.assertIs(result["ok"], True, result)
        self.assertEqual(result["status"], "ready", result)
        project = workspace.get_project(project_id)
        self.assertIs(project["active"], True, project)
        self.assertNotIn(project["status"], {"failed", "blocked"})
        self.assertEqual(project["execution"]["status"], "ready")
        task = _persisted_task(workspace, project_id, task_id)
        self.assertEqual(task["status"], "open", task)
        self.assertNotIn("error", task)
        for container_name in ("steps", "substeps", "execution_steps"):
            child = task[container_name][0]
            self.assertEqual(child["status"], "pending", child)
            self.assertEqual(child["state"], "pending", child)
            self.assertEqual(child["completion_status"], "pending", child)
            for stale_key in ("error", "result", "retry_count"):
                self.assertNotIn(stale_key, child)

    def test_failed_nested_child_aliases_are_not_retried(self):
        for container_name in ("steps", "substeps", "execution_steps"):
            with self.subTest(container_name=container_name):
                workspace, _state, _orchestrator, controller, sandbox = (
                    _build_real_pipeline(self.tmp_path / container_name)
                )
                project_id, task_id = _create_project_with_task(
                    workspace,
                    action="implement",
                    target_file=f"{container_name}-retry.txt",
                    content="must not be retried",
                )

                def seed_failed_child(_project, task):
                    task["steps"] = []
                    task.pop("substeps", None)
                    task.pop("execution_steps", None)
                    task[container_name] = [
                        {
                            "id": f"{container_name}-failed-child",
                            "action": "implement",
                            "target_file": f"{container_name}-retry.txt",
                            "content": "must not be retried",
                            "status": "failed",
                            "error": f"{container_name} child failed",
                        }
                    ]

                _mutate_persisted_task(
                    workspace, project_id, task_id, seed_failed_child
                )
                execution_calls = []
                controller._execute_with_existing_orchestrator = (
                    lambda **kwargs: execution_calls.append(kwargs)
                )

                result = controller.run_all(project_id)

                self.assertIs(result["ok"], False, result)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(execution_calls, [])
                persisted_task = _persisted_task(
                    workspace, project_id, task_id
                )
                self.assertEqual(
                    persisted_task["status"], "failed", persisted_task
                )
                self.assertEqual(
                    persisted_task["error"],
                    f"{container_name} child failed",
                )
                self.assertFalse(
                    (sandbox / f"{container_name}-retry.txt").exists()
                )

    def test_substeps_only_task_executes_the_real_child_contract(self):
        workspace, _state, _orchestrator, controller, sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project_id, task_id = _create_project_with_task(
            workspace,
            description="Execution details are supplied only by substeps.",
        )

        def install_substeps(_project, task):
            task["action"] = ""
            task["steps"] = []
            task["target_file"] = ""
            task["content"] = ""
            task["substeps"] = [
                {
                    "id": "substeps-real-child",
                    "title": "Write from substeps",
                    "action": "implement",
                    "target_file": "substeps-output.txt",
                    "content": "written by substeps",
                    "status": "pending",
                }
            ]

        _mutate_persisted_task(workspace, project_id, task_id, install_substeps)

        result = controller.run_all(project_id)

        self.assertIs(result["ok"], True, result)
        self.assertEqual(result["status"], "completed", result)
        self.assertEqual(
            (sandbox / "substeps-output.txt")
            .read_text(encoding="utf-8")
            .strip(),
            "written by substeps",
        )
        task = _persisted_task(workspace, project_id, task_id)
        self.assertEqual(task["status"], "completed", task)
        self.assertEqual(task["substeps"][0]["status"], "completed", task)

    def test_finished_success_alias_is_not_reexecuted(self):
        workspace, _state, _orchestrator, controller, sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project_id, task_id = _create_project_with_task(
            workspace,
            action="implement",
            target_file="finished-alias.txt",
            content="must not run again",
        )

        _mutate_persisted_task(
            workspace,
            project_id,
            task_id,
            lambda _project, task: task.update({"status": "finished"}),
        )
        execution_calls = []
        controller._execute_with_existing_orchestrator = (
            lambda **kwargs: execution_calls.append(kwargs)
        )

        result = controller.run_all(project_id)

        self.assertIs(result["ok"], True, result)
        self.assertEqual(result["status"], "completed", result)
        self.assertEqual(execution_calls, [])
        self.assertEqual(
            _persisted_task(workspace, project_id, task_id)["status"],
            "finished",
        )
        self.assertFalse((sandbox / "finished-alias.txt").exists())

    def test_waiting_and_stopped_statuses_are_non_runnable_and_preserved(self):
        expected_results = {
            "needs_input": "waiting",
            "waiting_input": "waiting",
            "awaiting_approval": "waiting_approval",
            "stopped": "stopped",
        }
        for task_status, expected_result in expected_results.items():
            with self.subTest(task_status=task_status):
                workspace, _state, _orchestrator, controller, sandbox = (
                    _build_real_pipeline(self.tmp_path / task_status)
                )
                project_id, task_id = _create_project_with_task(
                    workspace,
                    action="implement",
                    target_file=f"{task_status}.txt",
                    content="must wait",
                )
                preserved_reason = f"preserve {task_status} reason"

                def seed_waiting(_project, task):
                    task["status"] = task_status
                    task["error"] = preserved_reason

                _mutate_persisted_task(
                    workspace, project_id, task_id, seed_waiting
                )
                execution_calls = []
                controller._execute_with_existing_orchestrator = (
                    lambda **kwargs: execution_calls.append(kwargs)
                )

                result = controller.run_all(project_id)

                self.assertEqual(result["status"], expected_result, result)
                self.assertEqual(execution_calls, [])
                task = _persisted_task(workspace, project_id, task_id)
                self.assertEqual(task["status"], task_status, task)
                self.assertEqual(task["error"], preserved_reason)
                self.assertFalse((sandbox / f"{task_status}.txt").exists())

    def test_existing_blocker_text_is_not_overwritten(self):
        workspace, _state, _orchestrator, controller, _sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project_id, task_id = _create_project_with_task(
            workspace,
            action="implement",
            dependencies=["missing-dependency"],
            target_file="blocked.txt",
            content="blocked",
        )
        original_blocker = "Waiting for the signed design approval."

        def seed_blocker(_project, task):
            task["error"] = original_blocker
            task["blocked_reason"] = original_blocker

        _mutate_persisted_task(workspace, project_id, task_id, seed_blocker)

        result = controller.run_all(project_id)

        self.assertIs(result["ok"], False, result)
        self.assertEqual(result["status"], "blocked", result)
        task = _persisted_task(workspace, project_id, task_id)
        self.assertEqual(task["status"], "blocked", task)
        self.assertEqual(task["error"], original_blocker)
        self.assertEqual(task["blocked_reason"], original_blocker)

    def test_running_execution_maps_project_status_to_in_progress(self):
        workspace, _state, _orchestrator, _controller, _sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project_id, task_id = _create_project_with_task(
            workspace,
            action="implement",
            target_file="running.txt",
            content="running",
        )

        workspace.update_execution_state(
            project_id,
            status="running",
            current_task_id=task_id,
            current_step="Running task",
            queue=[task_id],
            last_action="run_all",
        )

        project = workspace.get_project(project_id)
        self.assertEqual(project["execution"]["status"], "running")
        self.assertEqual(project["status"], "in_progress", project)

    def test_first_step_approval_falls_back_to_task_when_execution_has_no_steps(self):
        workspace, _state, _orchestrator, controller, sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project_id, task_id = _create_project_with_task(
            workspace,
            steps=[
                {
                    "id": "approval-first-child",
                    "title": "Approve first child",
                    "action": "implement",
                    "target_file": "approved-first-child.txt",
                    "content": "approved first child",
                    "status": "waiting_approval",
                    "requires_approval": True,
                    "approval_required": True,
                    "approval_status": "pending",
                }
            ],
        )
        workspace.update_execution_state(
            project_id,
            status="waiting_approval",
            current_task_id=task_id,
            current_step="Approve first child",
            current_step_index=0,
            queue=[task_id],
            last_action="run_all",
        )
        self.assertNotIn(
            "steps", workspace.get_execution_state(project_id)
        )

        result = controller.approve_project(project_id)

        self.assertIs(result["ok"], True, result)
        self.assertEqual(result["status"], "completed", result)
        self.assertEqual(
            (sandbox / "approved-first-child.txt")
            .read_text(encoding="utf-8")
            .strip(),
            "approved first child",
        )
        task = _persisted_task(workspace, project_id, task_id)
        self.assertEqual(task["status"], "completed", task)
        self.assertEqual(task["steps"][0]["status"], "completed", task)
        self.assertEqual(
            workspace.get_execution_state(project_id)["status"],
            "completed",
        )

    def test_orchestrator_exception_persists_current_task_and_project_failure(self):
        for advancing_action in ("continue", "run_all"):
            with self.subTest(advancing_action=advancing_action):
                workspace, _state, orchestrator, controller, _sandbox = (
                    _build_real_pipeline(self.tmp_path / advancing_action)
                )
                project_id, task_id = _create_project_with_task(
                    workspace,
                    action="implement",
                    target_file=f"{advancing_action}-exception.txt",
                    content="must fail",
                )

                def raise_from_process_execution(*_args, **_kwargs):
                    raise RuntimeError("canonical orchestrator exploded")

                orchestrator.process_execution = raise_from_process_execution
                if advancing_action == "continue":
                    result = controller.continue_project(project_id)
                else:
                    result = controller.run_all(project_id)

                self.assertIs(result["ok"], False, result)
                self.assertEqual(result["status"], "failed", result)
                task = _persisted_task(workspace, project_id, task_id)
                self.assertEqual(task["status"], "failed", task)
                self.assertIn("orchestrator exploded", task["error"])
                self.assertEqual(
                    workspace.get_execution_state(project_id)["status"],
                    "failed",
                )
                self.assertEqual(
                    workspace.get_project(project_id)["status"], "failed"
                )

    def test_run_all_safety_limit_never_returns_or_persists_running(self):
        workspace, _state, _orchestrator, controller, _sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project_id, task_id = _create_project_with_task(
            workspace,
            action="implement",
            target_file="safety-limit.txt",
            content="never finishes",
        )
        execution_calls = []

        def never_finishes(**_kwargs):
            execution_calls.append(task_id)
            return {
                "ok": True,
                "execution": {
                    "status": "running",
                    "complete": False,
                    "waiting": False,
                    "steps": [
                        {
                            "id": "safety-limit-step",
                            "task_id": task_id,
                            "status": "pending",
                        }
                    ],
                },
            }

        signature_counter = iter(range(1000))
        controller._execute_with_existing_orchestrator = never_finishes
        controller._project_progress_signature = (
            lambda _project: (next(signature_counter),)
        )

        result = controller.run_all(project_id)

        self.assertEqual(len(execution_calls), 100)
        self.assertIs(result["ok"], False, result)
        self.assertNotEqual(result["status"], "running", result)
        self.assertIn("safety limit", result["message"].lower())
        persisted = workspace.get_execution_state(project_id)
        self.assertNotEqual(persisted["status"], "running", persisted)
        self.assertEqual(result["status"], persisted["status"])

    def test_failed_approval_reports_failure_and_does_not_publish(self):
        workspace, _state, _orchestrator, controller, _sandbox = (
            _build_real_pipeline(self.tmp_path)
        )
        project_id, task_id = _create_project_with_task(
            workspace,
            steps=[
                {
                    "id": "approval-failure-child",
                    "title": "Approved child fails",
                    "action": "implement",
                    "target_file": "approval-failure.txt",
                    "content": "must fail",
                    "status": "waiting_approval",
                    "requires_approval": True,
                    "approval_required": True,
                    "approval_status": "pending",
                }
            ],
        )
        workspace.update_execution_state(
            project_id,
            status="waiting_approval",
            current_task_id=task_id,
            current_step_index=0,
            queue=[task_id],
            last_action="run_all",
        )
        controller._execute_with_existing_orchestrator = lambda **_kwargs: {
            "ok": False,
            "execution": {
                "status": "failed",
                "complete": False,
                "waiting": False,
                "error": "approved execution failed",
                "steps": [
                    {
                        "id": "approval-failure-runtime",
                        "task_id": task_id,
                        "step_id": "approval-failure-child",
                        "status": "failed",
                        "error": "approved execution failed",
                    }
                ],
            },
        }
        publish_calls = []
        controller._publish_completed_artifacts = (
            lambda *args, **kwargs: publish_calls.append((args, kwargs))
        )

        result = controller.approve_project(project_id)

        self.assertIs(result["ok"], False, result)
        self.assertEqual(result["status"], "failed", result)
        self.assertEqual(result["execution"]["status"], "failed")
        self.assertEqual(publish_calls, [])
        task = _persisted_task(workspace, project_id, task_id)
        self.assertEqual(task["status"], "failed", task)
        self.assertEqual(
            task["steps"][0]["error"], "approved execution failed"
        )
        self.assertEqual(workspace.get_project(project_id)["status"], "failed")

