from nova_backend.services.planner_service import planner_service


print("NOVA SELF IMPROVEMENT EXECUTION LOOP SMOKE")
print("========================================")


goal = "Improve conversation recall"


mission = planner_service.create_mission(goal)

print("MISSION CREATED:")
print(mission)


result = planner_service.advance_step(goal)

print()
print("AFTER FIRST STEP:")
print(result)


assert mission["goal"] == goal
assert result["current_index"] == 1
assert result["status"] == "running"

print()
print("PASS mission created")
print("PASS execution advanced")
print()
print("NOVA SELF IMPROVEMENT EXECUTION LOOP SMOKE PASSED")