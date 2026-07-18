from pathlib import Path
import json


class SessionDetailCacheService:

    def __init__(self):
        self._cache = {}


    def cache_path(self):
        return (
            Path(__file__).resolve().parents[2]
            /
            "data"
            /
            "nova_final_session_detail_cache.json"
        )


    def load_sessions_store(self):
        path = self.cache_path()

        if not path.exists():
            return {}

        try:
            return json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            return {}


    def save_sessions_store(self, store):
        self.cache_path().write_text(
            json.dumps(
                store,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


    def find_session_in_store(
        self,
        store,
        session_id,
    ):
        if not isinstance(store, dict):
            return None

        return store.get(
            str(session_id)
        )


    def upsert_session_in_store(
        self,
        session_id,
        session_obj,
    ):
        store = self.load_sessions_store()

        store[str(session_id)] = session_obj

        self.save_sessions_store(
            store
        )

        return session_obj