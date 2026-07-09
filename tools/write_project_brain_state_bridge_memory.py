from nova_backend.services.project_brain_state_bridge import write_state_bridge_memory, build_state_bridge_answer

result = write_state_bridge_memory(
    memory_path="data/nova_memory.json",
    operator_memory_path="data/project_brain_operator_memory.json",
    next_move="Project Brain State Recall Refresh v1",
)

print(build_state_bridge_answer(
    memory_path="data/nova_memory.json",
    operator_memory_path="data/project_brain_operator_memory.json",
    next_move="Project Brain State Recall Refresh v1",
    write=False,
))

print("")
print("WROTE:", result["item"]["id"])
