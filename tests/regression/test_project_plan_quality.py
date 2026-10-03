"""Isolated contract tests for deterministic project-plan quality checks."""

import importlib.util
from pathlib import Path
import unittest


SERVICE_PATH = (
    Path(__file__).resolve().parents[2]
    / "nova_backend"
    / "services"
    / "project_plan_quality_service.py"
)
SPEC = importlib.util.spec_from_file_location("project_plan_quality_service", SERVICE_PATH)
quality_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(quality_module)

ProjectPlanQualityService = quality_module.ProjectPlanQualityService
ProjectPlanValidationError = quality_module.ProjectPlanValidationError


def task(title, **values):
    result = {
        "id": title.lower().replace(" ", "_"),
        "title": title,
        "action": "write",
        "owner": "NOVA",
        "target_file": f"{title.lower().replace(' ', '_')}.md",
        "expected_output": f"A useful artifact for {title}.",
        "completion_criteria": f"Verify the artifact for {title}.",
        "dependencies": [],
        "steps": [{
            "id": f"{title.lower().replace(' ', '_')}_step",
            "title": "Gather the specific requirements",
            "action": "write",
            "owner": "NOVA",
            "target_file": f"{title.lower().replace(' ', '_')}.md",
            "content": "Planned content",
        }],
    }
    result.update(values)
    return result


class ProjectPlanQualityTests(unittest.TestCase):
    def setUp(self):
        self.service = ProjectPlanQualityService()

    def validate(self, tasks, **plan_fields):
        return self.service.validate({"tasks": tasks, **plan_fields}, request="Build a useful project")

    def test_valid_file_plan_preserves_targets_owner_and_goal_metadata(self):
        source = task("Create project brief")
        result = self.validate([source], complexity="small", work_type="writing")
        self.assertEqual(result["tasks"][0]["target_file"], source["target_file"])
        self.assertEqual(result["tasks"][0]["steps"][0]["target_file"], source["target_file"])
        self.assertEqual(result["tasks"][0]["owner"], "NOVA")
        self.assertEqual(result["goal"], "Build a useful project")
        self.assertEqual(result["complexity"], "small")
        self.assertEqual(result["work_type"], "writing")

    def test_file_operation_without_authoritative_target_is_rejected(self):
        source = task("Create project brief", target_file="", target_files=[], steps=[{
            "title": "Write the requested material", "action": "write", "target_file": ""
        }])
        with self.assertRaisesRegex(ProjectPlanValidationError, "no authoritative target file"):
            self.validate([source])

    def test_controller_meta_task_is_removed_without_losing_deliverable(self):
        result = self.validate([
            {"title": "Execute the first project task", "action": "run"},
            task("Create project brief"),
        ])
        self.assertEqual([item["title"] for item in result["tasks"]], ["Create project brief"])

    def test_duplicate_and_parent_step_paraphrases_are_rejected(self):
        with self.assertRaisesRegex(ProjectPlanValidationError, "overlapping project tasks"):
            self.validate([task("Create the launch brief"), task("Create launch brief")])
        with self.assertRaisesRegex(ProjectPlanValidationError, "repeats its parent"):
            self.validate([task("Create the launch brief", steps=[{
                "title": "Create the launch brief", "action": "write", "target_file": "brief.md"
            }])])

    def test_task_and_step_owners_are_validated_and_preserved(self):
        source = task("Confirm launch date", action="manual", owner="USER", target_file="")
        source["steps"] = [{"title": "Confirm the date", "action": "manual", "owner": "USER"}]
        result = self.validate([source])
        self.assertEqual(result["tasks"][0]["owner"], "USER")
        self.assertEqual(result["tasks"][0]["steps"][0]["owner"], "USER")
        source["owner"] = "UNSUPPORTED"
        with self.assertRaisesRegex(ProjectPlanValidationError, "Unsupported action owner"):
            self.validate([source])

    def test_unknown_tools_and_actions_are_rejected(self):
        source = task("Create project brief", tool_name="missing_tool")
        with self.assertRaisesRegex(ProjectPlanValidationError, "unsupported Nova tool"):
            self.service.validate({"tasks": [source]}, available_tools={"file_writer"})
        source = task("Create project brief", action="teleport")
        with self.assertRaisesRegex(ProjectPlanValidationError, "unsupported action"):
            self.validate([source])

    def test_dependencies_must_resolve_and_be_acyclic(self):
        first = task("Create project brief")
        second = task("Review project brief", action="review", target_file="", dependencies=[first["id"]])
        second["steps"] = [{"title": "Check that the brief meets its goal", "action": "review", "owner": "NOVA"}]
        validated = self.validate([first, second])
        self.assertEqual(validated["tasks"][1]["dependencies"], [first["id"]])
        second["dependencies"] = ["missing_task"]
        with self.assertRaisesRegex(ProjectPlanValidationError, "depends on missing task"):
            self.validate([first, second])
        first["dependencies"] = [second["id"]]
        second["dependencies"] = [first["id"]]
        with self.assertRaisesRegex(ProjectPlanValidationError, "contain a cycle"):
            self.validate([first, second])

    def test_missing_expected_output_gets_owner_appropriate_criteria(self):
        source = task(
            "Arrange venue", action="manual", owner="USER", target_file="",
            expected_output="", completion_criteria="",
        )
        source["steps"] = [{"title": "Confirm a suitable venue", "action": "manual", "owner": "USER"}]
        result = self.validate([source])
        self.assertIn("Real-world outcome", result["tasks"][0]["expected_output"])
        self.assertIn("user confirms", result["tasks"][0]["completion_criteria"].lower())

    def test_representative_goal_types_keep_structure_and_ownership_contextual(self):
        simple = self.validate(
            [task("Create greeting file")],
            phases=[{"id": "phase_1", "title": "Greeting"}],
        )
        self.assertEqual(simple["complexity"], "trivial")
        self.assertEqual(simple["phases"], [])

        moving = task(
            "Confirm moving date with the landlord",
            action="manual",
            owner="USER",
            target_file="",
            expected_output="Moving date confirmed",
            completion_criteria="User confirms the date",
        )
        moving["steps"] = [{
            "title": "Contact the landlord about the move date",
            "action": "manual",
            "owner": "USER",
        }]
        creative = task(
            "Draft the opening scene",
            action="write",
            target_file="opening_scene.md",
            expected_output="Opening scene draft in opening_scene.md",
        )
        creative["steps"] = [{
            "title": "Write the first scene from the outline",
            "action": "write",
            "owner": "NOVA",
            "target_file": "opening_scene.md",
            "content": "A planned opening scene",
        }]

        result = self.validate([moving, creative], work_type="creative writing")
        by_title = {item["title"]: item for item in result["tasks"]}
        self.assertEqual(by_title[moving["title"]]["owner"], "USER")
        self.assertEqual(by_title[creative["title"]]["owner"], "NOVA")
        self.assertEqual(result["work_type"], "creative writing")

    def test_mixed_owner_steps_are_rejected_to_prevent_boundary_bypass(self):
        source = task("Prepare and approve proposal")
        source["steps"] = [{
            "title": "Review the proposal with the user",
            "action": "review",
            "owner": "COLLABORATIVE",
        }]
        with self.assertRaisesRegex(ProjectPlanValidationError, "mixes ownership"):
            self.validate([source])

    def test_phase_paraphrases_and_empty_titles_are_rejected(self):
        simple = self.validate(
            [task("Create a launch brief")],
            phases=[{"title": "Create launch brief"}],
        )
        self.assertEqual(simple["phases"], [])
        with self.assertRaisesRegex(ProjectPlanValidationError, "repeats task"):
            self.validate(
                [
                    task("Create a launch brief"),
                    task("Research likely customers", action="research", target_file="", steps=[{
                        "title": "Identify customer needs", "action": "research", "owner": "NOVA"
                    }]),
                    task("Choose initial services"),
                ],
                phases=[{"title": "Create launch brief"}, {"title": "Customer research"}],
            )
        with self.assertRaisesRegex(ProjectPlanValidationError, "has no title"):
            self.validate([{"action": "analyze"}])

    def test_generic_file_output_and_criteria_are_repaired_from_target(self):
        source = task(
            "Create market comparison",
            expected_output="A completed implementation",
            completion_criteria="Done",
        )
        result = self.validate([source])
        normalized = result["tasks"][0]
        self.assertIn(normalized["target_file"], normalized["expected_output"])
        self.assertIn(normalized["target_file"], normalized["completion_criteria"])

    def test_step_target_drives_parent_expected_output(self):
        source = task(
            "Research neighborhood options",
            action="analyze",
            target_file="",
            expected_output="",
            completion_criteria="",
        )
        source["steps"] = [{
            "title": "Save comparison of neighborhood options",
            "action": "write",
            "owner": "NOVA",
            "target_file": "neighborhood_options.md",
            "content": "Comparison",
        }]
        result = self.validate([source])
        self.assertIn("neighborhood_options.md", result["tasks"][0]["expected_output"])
        self.assertIn("neighborhood_options.md", result["tasks"][0]["completion_criteria"])


if __name__ == "__main__":
    unittest.main()
