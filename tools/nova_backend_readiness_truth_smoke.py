from nova_backend.services.compute_backend_readiness import (
    DATA_DIR,
    MEMORY_FILE,
    SESSION_FILE,
    build_backend_readiness,
    count_items,
    load_json,
)


def check(name, passed, detail=""):
    if not passed:
        raise AssertionError(
            f"{name} FAILED. {detail}"
        )

    print(
        "PASS",
        name,
    )


print(
    "NOVA BACKEND READINESS TRUTH SMOKE"
)


data = build_backend_readiness()


check(
    "operational semantics",
    data.get("metric_semantics")
    ==
    "operational_capability_not_activity",
    repr(data),
)


check(
    "memory source is nova_memory.json",
    MEMORY_FILE.name
    ==
    "nova_memory.json",
    str(MEMORY_FILE),
)


check(
    "memory count real",
    data.get("memory_items")
    ==
    count_items(
        load_json(MEMORY_FILE)
    ),
    repr(data),
)


check(
    "session count real",
    data.get("session_records")
    ==
    count_items(
        load_json(SESSION_FILE)
    ),
    repr(data),
)


for key in (
    "execution_percent",
    "memory_percent",
    "agency_percent",
    "planner_percent",
    "session_percent",
):
    check(
        f"{key} ready",
        float(
            data.get(key, 0)
        )
        ==
        100.0,
        repr(data),
    )


check(
    "overall readiness full",
    float(
        data.get(
            "overall_backend_readiness",
            0,
        )
    )
    ==
    100.0,
    repr(data),
)


print(
    "DATA DIR:",
    DATA_DIR,
)

print(
    "MEMORY ITEMS:",
    data["memory_items"],
)

print(
    "SESSION RECORDS:",
    data["session_records"],
)

print(
    "NOVA BACKEND READINESS TRUTH SMOKE PASSED"
)
