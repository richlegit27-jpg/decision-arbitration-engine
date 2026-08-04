import json
import urllib.request


BASE = "http://127.0.0.1:5001"


def assert_true(name, condition):
    if not condition:
        raise AssertionError(
            f"{name} FAILED"
        )

    print(
        f"PASS {name}"
    )


def request_json(
    path,
    method="GET",
    body=None,
):
    data = None

    if body is not None:
        data = json.dumps(
            body
        ).encode("utf-8")

    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Content-Type": "application/json",
        },
    )

    with urllib.request.urlopen(req) as response:
        return json.loads(
            response.read().decode("utf-8")
        )


def main():
    created = request_json(
        "/api/projects/new",
        method="POST",
        body={
            "name": "Nova Workplace Test",
            "description": "API project test",
        },
    )

    assert_true(
        "project_create_api",
        created.get("ok") is True
        and created.get("project", {}).get("id"),
    )

    project_id = created["project"]["id"]

    listed = request_json(
        "/api/projects"
    )

    assert_true(
        "project_list_api",
        any(
            project.get("id") == project_id
            for project in listed.get(
                "projects",
                [],
            )
        ),
    )

    print()
    print(
        "NOVA PROJECT API SMOKE PASSED"
    )


if __name__ == "__main__":
    main()