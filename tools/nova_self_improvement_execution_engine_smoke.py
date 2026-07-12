from nova_backend.services.planner_service import planner_service
from nova_backend.services.chat_execution_service import chat_execution_service


print("NOVA SELF IMPROVEMENT EXECUTION ENGINE SMOKE")
print("===========================================")


goal = "Improve conversation recall"

mission = planner_service.create_mission(goal)

print("MISSION:")
print(mission)


session_id = "self_improvement_test_session"

steps = [
    "design",
    "implement",
    "test",
]


started = chat_execution_service.start(
    session_id,
    goal,
    steps,
)

print("STARTED:")
print(started)


chat_execution_service.attach_mission(
    session_id,
    mission["id"],
)


advanced = chat_execution_service.advance(
    session_id,
)

print("ADVANCED:")
print(advanced)


assert advanced["current_index"] == 1
assert advanced["mission_id"] == mission["id"]


print("PASS execution engine attached")
print("PASS mission progress bridge")
print("NOVA SELF IMPROVEMENT EXECUTION ENGINE SMOKE PASSED")