from pathlib import Path
from tempfile import TemporaryDirectory

from nova_backend.services.mission_service import (
    MissionService,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(
            f"{name} FAILED {detail}"
        )

    print(f"PASS {name}")


def main():
    with TemporaryDirectory() as temp_dir:
        state_path = (
            Path(temp_dir)
            / "missions.json"
        )

        service = MissionService(
            state_path=str(state_path)
        )

        created = service.create_mission(
            goal="Test mission persistence",
            steps=[
                "first step",
                "second step",
            ],
        )

        mission_id = created["id"]

        assert_true(
            "mission_created",
            created.get("status") == "ready",
            created,
        )

        service.start_mission(mission_id)

        advanced = service.advance_step(
            mission_id,
            {
                "result": "first step complete",
            },
        )

        assert_true(
            "mission_advanced",
            advanced.get("current_step") == 1,
            advanced,
        )

        restarted_service = MissionService(
            state_path=str(state_path)
        )

        restored = restarted_service.get_mission(
            mission_id
        )

        assert_true(
            "mission_survives_restart",
            isinstance(restored, dict),
            restored,
        )

        assert_true(
            "mission_status_preserved",
            restored.get("status") == "running",
            restored,
        )

        assert_true(
            "mission_progress_preserved",
            restored.get("current_step") == 1,
            restored,
        )

        assert_true(
            "mission_results_preserved",
            len(restored.get("results", [])) == 1,
            restored,
        )

        print(
            "\nNOVA MISSION PERSISTENCE "
            "SMOKE PASSED"
        )


if __name__ == "__main__":
    main()