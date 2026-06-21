class MemoryCore:
    """
    Simple memory system for Nova.
    Stores and retrieves structured context.
    """

    def __init__(self):
        self.store = []

    def add(self, item: dict):
        self.store.append(item)

    def get_recent(self, limit: int = 10):
        return self.store[-limit:]

    def clear(self):
        self.store = []

