import time
import json
import os


class UsageTracker:
    """
    Tracks usage for billing (MVP system)
    """

    def __init__(self, storage_path="data/usage.json"):
        self.storage_path = storage_path
        self.ensure_dir()

    def ensure_dir(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

    def log_event(self, user_id: str, action: str, metadata: dict = None):
        event = {
            "user_id": user_id,
            "action": action,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }

        data = self._load()

        data.append(event)

        self._save(data)

        return event

    def get_usage(self, user_id: str):
        data = self._load()
        return [x for x in data if x["user_id"] == user_id]

    def calculate_cost(self, user_id: str):
        usage = self.get_usage(user_id)

        cost_map = {
            "chat.send": 0.001,
            "email.send": 0.01,
            "calendar.create": 0.005,
            "attachment.analyze": 0.02
        }

        total = 0.0

        for u in usage:
            total += cost_map.get(u["action"], 0.0)

        return round(total, 4)

    def _load(self):
        if not os.path.exists(self.storage_path):
            return []

        with open(self.storage_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data):
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)