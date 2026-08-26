from nova_backend.services.memory_service import MemoryService

memory = MemoryService(
    ".\\data\\nova_memory.json"
)

result = memory.add_memory(
    {
        "text": "my name is Richard",
        "kind": "user_fact",
        "source": "direct_memory_test",
    }
)

print("SAVED:")
print(result)

print("\nCURRENT MEMORY MATCHES:")

data = memory._read_store()

for item in data.get("memory", []):
    if "Richard" in str(item.get("text")):
        print(item)