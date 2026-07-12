from pathlib import Path
from tempfile import TemporaryDirectory

from nova_backend.services.persistent_project_registry import (
    PROJECT_COLLECTIONS,
    PersistentProjectRegistry,
)


def require(condition, message, evidence=None):
    if not condition:
        raise AssertionError(
            message
            + (
                "\nEVIDENCE: "
                + repr(evidence)
                if evidence is not None
                else ""
            )
        )

    print("PASS", message)


print("=" * 100)
print("PHASE 8A PERSISTENT PROJECT REGISTRY SMOKE")
print("=" * 100)


with TemporaryDirectory() as temporary:
    path = (
        Path(temporary)
        / "nova_projects.json"
    )

    registry = PersistentProjectRegistry(path)

    empty = registry.load()

    require(
        empty["version"] == 1,
        "schema version is locked",
        empty,
    )
    require(
        empty["projects"] == [],
        "new registry starts empty",
        empty,
    )

    nova = registry.create_project(
        title="Nova",
        description="Persistent AI operating system",
        metadata={"owner": "Richard"},
    )

    require(
        nova["id"] == "nova",
        "stable project id created",
        nova,
    )
    require(
        tuple(
            key
            for key in PROJECT_COLLECTIONS
            if key in nova
        ) == PROJECT_COLLECTIONS,
        "all operating-system collections exist",
        nova.keys(),
    )

    ensured = registry.ensure_project(
        title="Nova",
    )

    require(
        ensured["id"] == nova["id"],
        "ensure_project reuses canonical project",
        ensured,
    )
    require(
        len(registry.list_projects()) == 1,
        "ensure_project does not duplicate project",
        registry.list_projects(),
    )

    for collection in PROJECT_COLLECTIONS:
        record = registry.add_record(
            project_id=nova["id"],
            collection=collection,
            title=f"Test {collection}",
            details=(
                f"Persistent {collection} contract"
            ),
        )

        require(
            bool(record["id"]),
            f"{collection} record receives identity",
            record,
        )

    active = registry.get_active_project()

    require(
        active is not None,
        "active project resolves",
        active,
    )
    require(
        active["id"] == "nova",
        "first project becomes active",
        active,
    )

    for collection in PROJECT_COLLECTIONS:
        require(
            len(active[collection]) == 1,
            f"{collection} persists exactly once",
            active[collection],
        )

    reloaded = PersistentProjectRegistry(path)
    reloaded_nova = reloaded.get_project("nova")

    require(
        reloaded_nova == active,
        "registry survives full service reload",
        reloaded_nova,
    )
    require(
        not path.with_name(
            path.name + ".tmp"
        ).exists(),
        "atomic write leaves no temporary file",
    )

    try:
        reloaded.get_project(
            "missing-project"
        )
    except KeyError:
        print(
            "PASS unknown project fails explicitly"
        )
    else:
        raise AssertionError(
            "unknown project did not fail"
        )


print()
print("=" * 100)
print("PHASE 8A PERSISTENT PROJECT REGISTRY: REAL PASS")
print("MULTI-PROJECT SOURCE OF TRUTH: LOCKED")
print("GOALS / DEADLINES / DECISIONS / DOCUMENTS / WORKFLOWS / KNOWLEDGE: PERSISTENT")
print("=" * 100)
