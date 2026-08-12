from __future__ import annotations

from typing import Any, Dict


class NovaTool:
    name = ""
    description = ""

    def run(self, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError