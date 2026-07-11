"""
NOVA IMPROVEMENT HISTORY STORE V1

Persistent storage for self-improvement attempts.
"""

import json
from pathlib import Path
from datetime import datetime, timezone


DEFAULT_PATH = Path(
    "data/nova_improvement_history.json"
)


class NovaImprovementHistoryStore:


    def __init__(
        self,
        path=None
    ):

        self.path = Path(
            path or DEFAULT_PATH
        )

        self.path.parent.mkdir(
            exist_ok=True
        )


    def load(self):

        if not self.path.exists():

            return {
                "history": []
            }


        try:

            with open(
                self.path,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(file)


            if "history" not in data:

                data["history"] = []


            return data


        except Exception:

            return {
                "history": []
            }



    def save(
        self,
        data
    ):

        with open(
            self.path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False
            )


        return data



    def add(
        self,
        entry
    ):

        data = self.load()


        item = dict(
            entry
        )


        item.setdefault(
            "timestamp",
            datetime.now(
                timezone.utc
            ).isoformat()
        )


        data["history"].append(
            item
        )


        self.save(data)

        return item



    def get_all(self):

        return self.load().get(
            "history",
            []
        )