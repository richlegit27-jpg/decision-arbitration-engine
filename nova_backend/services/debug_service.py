from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


class DebugService:
    def __init__(self) -> None:
        self._state: Dict[str, Any] = {}

    def get_state(self) -> Dict[str, Any]:
        return deepcopy(self._state)

    def set_state(self, payload: Dict[str, Any] | None) -> Dict[str, Any]:
        self._state = deepcopy(payload or {})
        return self.get_state()

    def update_state(self, payload: Dict[str, Any] | None) -> Dict[str, Any]:
        if isinstance(payload, dict):
            self._state.update(deepcopy(payload))
        return self.get_state()

    def clear_state(self) -> Dict[str, Any]:
        self._state = {}
        return self.get_state()

    def snapshot(self, **extra: Any) -> Dict[str, Any]:
        data = self.get_state()
        if extra:
            data.update(deepcopy(extra))
        return data


__all__ = ["DebugService"]