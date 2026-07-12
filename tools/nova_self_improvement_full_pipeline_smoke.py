from nova_backend.services.nova_self_improvement_recommender import (
    create_self_improvement_recommendation,
)

from nova_backend.services.nova_upgrade_decision_engine import (
    create_upgrade_decision,
)

from nova_backend.services.nova_improvement_proposal import (
    create_improvement_proposal,
)

from nova_backend.services.mission_proposal_service import (
    create_mission_proposal,
)

from nova_backend.services.nova_improvement_report_service import (
    report_service,
)

from nova_backend.services.planner_service import (
    planner_service,
)


print("NOVA SELF IMPROVEMENT FULL PIPELINE SMOKE")
print("========================================")


behavior_priority = {
    "focus": "continuity",
    "priority": "medium",
    "reason": "continuity detected repeatedly",
}


print("STEP 1: CREATE RECOMMENDATION")

recommendation = create_self_improvement_recommendation(
    behavior_priority
)

assert recommendation["problem"] == "continuity"

print("PASS recommendation")


print("STEP 2: CREATE UPGRADE DECISION")

upgrade_decision = create_upgrade_decision(
    recommendation
)

assert upgrade_decision["decision"] == "consider_upgrade"

print("PASS decision")


print("STEP 3: CREATE IMPROVEMENT PROPOSAL")

improvement_proposal = create_improvement_proposal(
    recommendation
)

assert improvement_proposal["type"] == "improvement_proposal"

print("PASS proposal")


print("STEP 4: CREATE MISSION PROPOSAL")

mission_proposal = create_mission_proposal(
    improvement_proposal
)

assert mission_proposal["type"] == "mission_proposal"
assert mission_proposal["approval_required"] is True
assert mission_proposal["status"] == "proposal"

print("PASS mission proposal")


print("STEP 5: CREATE REPORT")

report = report_service.create_report(
    recommendation,
    upgrade_decision,
    improvement_proposal,
    mission_proposal,
)

print(report)

assert report["type"] == "improvement_report"
assert report["detected_problem"] == "continuity"
assert report["approval_required"] is True

print("PASS report")


print("STEP 6: CREATE MISSION")

mission = planner_service.create_mission(
    report["recommended_upgrade"]
)

assert mission["status"] == "ready"

print("PASS mission")


print("STEP 7: EXECUTE FIRST STEP")

execution = planner_service.advance_step(
    report["recommended_upgrade"]
)

assert execution["current_index"] == 1
assert execution["status"] == "running"

print("PASS execution")


print()
print("NOVA SELF IMPROVEMENT FULL PIPELINE SMOKE PASSED")