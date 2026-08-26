import json

from nova_backend.services.memory_context_service import MemoryContextService


class DummySession:
    pass


service = MemoryContextService(
    ".\\data",
    DummySession(),
)


with open(
    ".\\data\\nova_memory.json",
    "r",
    encoding="utf-8",
) as f:
    data = json.load(f)


results = service.rank_memory_items(
    data["memory"],
    user_text="what is my name",
)


for item in results[:10]:
    print(
        item["score"],
        "|",
        item["content"],
    )