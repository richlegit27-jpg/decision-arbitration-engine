from __future__ import annotations

import inspect
from typing import Any, Dict

from nova_backend.tools.risk_policy import tool_risk_metadata


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

        risk = tool_risk_metadata(self.name, self)
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
            "requires_approval": risk["requires_approval"],
            "risk_class": risk["risk_class"],
            "implemented": self.__class__.run is not NovaTool.run,
            "parameter_schema": self.parameter_schema(),
            "class": (
                self.__class__.__name__
            ),
            "module": (
                self.__class__.__module__
            ),
        }

    def parameter_schema(self) -> Dict[str, Any]:
        """Infer a conservative JSON-schema contract from run() parameters."""
        properties = {}
        required = []
        try:
            parameters = inspect.signature(self.run).parameters.values()
        except (TypeError, ValueError):
            parameters = ()
        for parameter in parameters:
            if parameter.name in {"kwargs", "args"} or parameter.kind in (
                inspect.Parameter.VAR_KEYWORD,
                inspect.Parameter.VAR_POSITIONAL,
            ):
                continue
            annotation = parameter.annotation
            types = {str: "string", int: "integer", float: "number", bool: "boolean", list: "array", dict: "object"}
            inferred = types.get(annotation)
            if inferred is None and isinstance(annotation, str):
                inferred = {
                    "str": "string", "int": "integer", "float": "number",
                    "bool": "boolean", "list": "array", "dict": "object",
                }.get(annotation.strip().lower())
            if inferred is None and parameter.default is not inspect.Parameter.empty:
                inferred = types.get(type(parameter.default))
            prop = {"type": inferred or "string"}
            if parameter.default is inspect.Parameter.empty:
                required.append(parameter.name)
            properties[parameter.name] = prop
        schema = {"type": "object", "properties": properties, "additionalProperties": False}
        if required:
            schema["required"] = required
        return schema


    def run(
        self,
        **kwargs,
    ) -> Dict[str, Any]:

        raise NotImplementedError(
            f"{self.__class__.__name__} "
            "must implement run()."
        )
