from __future__ import annotations

from typing import Any, Dict


class NovaTool:

    name = ""

    description = ""

    category = "general"

    capabilities = []

    risk_level = "low"

    requires_confirmation = False


    def get_metadata(
        self,
    ) -> Dict[str, Any]:

        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "capabilities": list(
                self.capabilities
            ),
            "risk_level": self.risk_level,
            "requires_confirmation": (
                self.requires_confirmation
            ),
            "class": (
                self.__class__.__name__
            ),
            "module": (
                self.__class__.__module__
            ),
        }


    def run(
        self,
        **kwargs,
    ) -> Dict[str, Any]:

        raise NotImplementedError(
            f"{self.__class__.__name__} "
            "must implement run()."
        )