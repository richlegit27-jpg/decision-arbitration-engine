from nova_backend.services.project_workspace_service import (
    ProjectWorkspaceService,
)


def assert_true(name, condition):
    if not condition:
        raise AssertionError(
            f"{name} FAILED"
        )

    print(
        f"PASS {name}"
    )


def main():
    service = ProjectWorkspaceService(
        data_dir="data"
    )

    project = service.create_project(
        "Nova Workplace Test",
        "Testing project workspace foundation",
    )

    assert_true(
        "project_created",
        isinstance(project, dict)
        and project.get("id"),
    )

    projects = service.list_projects()

    assert_true(
        "project_saved",
        any(
            item.get("id") == project.get("id")
            for item in projects
        ),
    )

    loaded = service.get_project(
        project["id"]
    )

    assert_true(
        "project_loaded",
        loaded is not None
        and loaded.get("name")
        == "Nova Workplace Test",
    )

    print()
    print(
        "NOVA PROJECT WORKSPACE SMOKE PASSED"
    )


if __name__ == "__main__":
    main()