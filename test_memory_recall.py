from nova_backend.services.memory_context_service import MemoryContextService

service = MemoryContextService(
    ".\data"
)

result = service.get_memory_context(
    "what is my name"
)

print(result)