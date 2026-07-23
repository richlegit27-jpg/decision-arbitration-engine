from pathlib import Path
from tempfile import TemporaryDirectory

from flask import Flask, session

from nova_backend.services.memory_service import (
    MemoryService,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(
            f"{name} FAILED {detail}"
        )

    print(f"PASS {name}")


app = Flask(__name__)
app.secret_key = "nova-memory-ownership-smoke"


with TemporaryDirectory() as temporary_directory:
    memory_path = (
        Path(temporary_directory)
        / "memory_ownership.json"
    )

    memory = MemoryService(
        str(memory_path)
    )

    with app.test_request_context("/"):
        session["nova_user_id"] = "user_a"

        saved_a = memory.add_memory(
            {
                "text": "User A private memory",
                "kind": "fact",
            }
        )

        visible_a = memory.all()

        assert_true(
            "user_a_memory_owned",
            saved_a.get("owner_id") == "user_a",
            saved_a,
        )

        assert_true(
            "user_a_sees_own_memory",
            len(visible_a) == 1
            and visible_a[0].get("owner_id")
            == "user_a",
            visible_a,
        )

    with app.test_request_context("/"):
        session["nova_user_id"] = "user_b"

        visible_b_before = memory.all()

        assert_true(
            "user_b_cannot_see_user_a_memory",
            visible_b_before == [],
            visible_b_before,
        )

        saved_b = memory.add_memory(
            {
                "text": "User B private memory",
                "kind": "fact",
            }
        )

        visible_b_after = memory.all()

        assert_true(
            "user_b_memory_owned",
            saved_b.get("owner_id") == "user_b",
            saved_b,
        )

        assert_true(
            "user_b_sees_only_own_memory",
            len(visible_b_after) == 1
            and visible_b_after[0].get("owner_id")
            == "user_b"
            and visible_b_after[0].get("text")
            == "User B private memory",
            visible_b_after,
        )

    with app.test_request_context("/"):
        session["nova_user_id"] = "user_a"

        visible_a_final = memory.all()

        assert_true(
            "user_a_still_sees_only_own_memory",
            len(visible_a_final) == 1
            and visible_a_final[0].get("owner_id")
            == "user_a"
            and visible_a_final[0].get("text")
            == "User A private memory",
            visible_a_final,
        )

        assert_true(
            "owner_memory_ids_are_distinct",
            saved_a.get("id") != saved_b.get("id"),
            {
                "user_a_id": saved_a.get("id"),
                "user_b_id": saved_b.get("id"),
            },
        )


print(
    "\nNOVA MEMORY OWNERSHIP SMOKE PASSED"
)