from app import project_execution_controller


PROJECT_ID = "test-project-dependency-gate"


def get_tasks():
    return [
        {
            "id": "project_task_gate-1",
            "task_id": "gate-1",
            "task_title": "Completed dependency",
            "title": "Completed dependency",
            "description": "A dependency that is already complete.",
            "action": "implement",
            "status": "completed",
            "target_file": r"C:\Users\Owner\nova\dependency_gate_one.py",
            "content": 'VALUE_ONE = "ONE"\n',
            "result": {
                "files": [
                    {
                        "file_path": r"C:\Users\Owner\nova\dependency_gate_one.py",
                        "written": True,
                        "compiled": True,
                    }
                ],
                "compiled": True,
            },
        },
        {
            "id": "project_task_gate-2",
            "task_id": "gate-2",
            "task_title": "Incomplete dependency",
            "title": "Incomplete dependency",
            "description": "A dependency that must remain incomplete.",
            "action": "implement",
            "status": "pending",
            "target_file": r"C:\Users\Owner\nova\dependency_gate_two.py",
            "content": 'VALUE_TWO = "TWO"\n',
        },
        {
            "id": "project_task_gate-3",
            "task_id": "gate-3",
            "task_title": "Blocked converged task",
            "title": "Blocked converged task",
            "description": "This task requires both dependencies.",
            "action": "implement",
            "status": "pending",
            "dependencies": ["gate-1", "missing-dependency"],
            "target_file": r"C:\Users\Owner\nova\dependency_gate_final.py",
            "content": 'FINAL_VALUE = "FINAL"\n',
        },
    ]


def main():
    tasks = get_tasks()

    result = (
        project_execution_controller
        ._execute_with_existing_orchestrator(
            project_id=PROJECT_ID,
            tasks=tasks,
            command="run_all",
        )
    )

    print("\nRESULT:")
    print(result)

    execution = result.get("execution", result)
    returned_steps = execution.get("steps", [])

    final_task = next(
        step
        for step in returned_steps
        if step.get("task_id") in {
            "gate-3",
            "project_task_gate-3",
        }
    )

    assert final_task.get("status") != "completed", (
        "Final task incorrectly completed while a dependency was unresolved"
    )

    assert final_task.get("status") in {
        "pending",
        "blocked",
        "waiting",
        "active",
    }, final_task

    print("\nDEPENDENCY GATE TEST PASSED")
    print("Final task status =", final_task.get("status"))


if __name__ == "__main__":
    main()