from nova_backend.services.project_workspace_service import (
    ProjectWorkspaceService,
)

from nova_backend.services.project_builder_service import (
    ProjectBuilderService,
)

from nova_backend.services.chat_execution_service import (
    chat_execution_service,
)

from nova_backend.services.project_execution_controller import (
    ProjectExecutionController,
)


DATA_DIR = (
    r"C:\Users\Owner\nova\data\backend_test_projects"
)


workspace = ProjectWorkspaceService(
    data_dir=DATA_DIR,
)


builder = ProjectBuilderService(
    workspace
)


print()
print("=" * 70)
print("BUILDING TEST PROJECT")
print("=" * 70)


request = (
    "I want to be a podcaster like Hasan Piker"
)


build_result = builder.build_project_from_request(
    user_text=request,
)


project = build_result.get(
    "project",
    {},
)


project_id = project.get(
    "id"
)


print()
print("PROJECT ID:")
print(project_id)


print()
print("PROJECT NAME:")
print(
    project.get("name")
)


print()
print("INITIAL TASKS:")


initial_tasks = project.get(
    "tasks",
    [],
)


for index, task in enumerate(
    initial_tasks,
    start=1,
):
    print(
        f"{index}. "
        f"{task.get('title')} "
        f"[{task.get('status')}] "
        f"ACTION={task.get('action')}"
    )


print()
print("=" * 70)
print("CREATING EXECUTION CONTROLLER")
print("=" * 70)


controller = ProjectExecutionController(
    project_workspace_service=workspace,
    chat_execution_service=(
        chat_execution_service
    ),
)


print()
print("=" * 70)
print("EXECUTION SERVICE IDENTITY CHECK")
print("=" * 70)


print(
    "IMPORTED CHAT EXECUTION SERVICE:",
    chat_execution_service,
)


print(
    "CONTROLLER CHAT EXECUTION SERVICE:",
    controller.chat_execution_service,
)


print(
    "SAME OBJECT:",
    controller.chat_execution_service
    is chat_execution_service,
)


print(
    "GET EXECUTION SERVICE:",
    controller._get_execution_service(),
)


print(
    "IS NONE:",
    controller._get_execution_service()
    is None,
)


print()
print("=" * 70)
print("RUNNING PROJECT")
print("=" * 70)


execution_result = controller.run_all(
    project_id
)


print()
print("RUN_ALL RESULT TYPE:")


print(
    type(execution_result)
)


print()
print("RUN_ALL RESULT:")


print(
    execution_result
)


print()
print("=" * 70)
print("FINAL PROJECT STATE")
print("=" * 70)


final_project = workspace.get_project(
    project_id
)


final_tasks = final_project.get(
    "tasks",
    [],
)


completed_count = 0


for index, task in enumerate(
    final_tasks,
    start=1,
):

    status = str(
        task.get(
            "status",
            "",
        )
    ).lower()

    if status in {
        "completed",
        "complete",
        "done",
    }:
        completed_count += 1

    print()

    print(
        f"{index}. "
        f"{task.get('title')}"
    )

    print(
        "   STATUS:",
        repr(
            task.get("status")
        ),
    )

    print(
        "   ACTION:",
        repr(
            task.get("action")
        ),
    )

    print(
        "   RESULT:",
        repr(
            task.get("result")
        ),
    )

    print(
        "   ERROR:",
        repr(
            task.get("error")
        ),
    )


print()
print("=" * 70)
print("EXECUTION SUMMARY")
print("=" * 70)


print(
    "TOTAL TASKS:",
    len(final_tasks),
)


print(
    "COMPLETED TASKS:",
    completed_count,
)


print(
    "REMAINING TASKS:",
    len(final_tasks) - completed_count,
)


execution_state = (
    workspace.get_execution_state(
        project_id
    )
)


print()
print("EXECUTION STATE:")


print(
    execution_state
)