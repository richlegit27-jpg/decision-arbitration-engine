from pathlib import Path
from tempfile import TemporaryDirectory

from nova_backend.services.memory_service import (
    MemoryService,
)


class TestMemoryService(MemoryService):
    def _current_owner_id(self) -> str:
        return "user_test"


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(
            f"{name} FAILED {detail}"
        )

    print(f"PASS {name}")


def main():
    with TemporaryDirectory() as temp_dir:
        memory_file = (
            Path(temp_dir)
            / "memory.json"
        )

        service = TestMemoryService(
            memory_file=str(memory_file)
        )

        created = service.add_memory(
            {
                "text": "Remember this test memory",
                "kind": "note",
                "owner_id": "user_test",
                "pinned": False,
            }
        )

        memory_id = created.get("id")

        assert_true(
            "memory_created",
            bool(memory_id),
            created,
        )

        restarted = TestMemoryService(
            memory_file=str(memory_file)
        )

        restored = restarted.get(memory_id)

        assert_true(
            "memory_survives_restart",
            isinstance(restored, dict),
            restored,
        )

        assert_true(
            "memory_text_preserved",
            restored.get("text")
            == "Remember this test memory",
            restored,
        )

        pinned = restarted.pin_memory(
            memory_id,
            pinned=True,
        )

        assert_true(
            "memory_pin_updated",
            pinned.get("pinned") is True,
            pinned,
        )

        restarted_after_pin = TestMemoryService(
            memory_file=str(memory_file)
        )

        restored_pinned = (
            restarted_after_pin.get(memory_id)
        )

        assert_true(
            "memory_pin_survives_restart",
            restored_pinned.get("pinned") is True,
            restored_pinned,
        )

        deleted = (
            restarted_after_pin.delete_memory(
                memory_id
            )
        )

        assert_true(
            "memory_deleted",
            deleted is True,
            deleted,
        )

        restarted_after_delete = TestMemoryService(
            memory_file=str(memory_file)
        )

        assert_true(
            "deleted_memory_stays_deleted",
            restarted_after_delete.get(memory_id)
            is None,
            restarted_after_delete.all(),
        )

        print(
            "\nNOVA MEMORY PERSISTENCE "
            "SMOKE PASSED"
        )


if __name__ == "__main__":
    main()