from __future__ import annotations

import inspect
from typing import Any, Callable, get_type_hints

_registry: dict[str, ToolEntry] = {}

PYTHON_TYPE_TO_JSON = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


class ToolEntry:
    def __init__(self, name: str, description: str, func: Callable):
        self.name = name
        self.description = description
        self.func = func
        self.schema = self._build_schema()

    def _build_schema(self) -> dict[str, Any]:
        hints = get_type_hints(self.func)
        hints.pop("return", None)
        sig = inspect.signature(self.func)

        properties = {}
        required = []

        SKIP_PARAMS = {"db", "session"}

        for param_name, param in sig.parameters.items():
            if param_name in SKIP_PARAMS:
                continue
            param_type = hints.get(param_name, str)
            base_type = param_type
            is_optional = False

            origin = getattr(param_type, "__origin__", None)
            if origin is type(None):
                is_optional = True
            args = getattr(param_type, "__args__", None)
            if args and type(None) in args:
                is_optional = True
                base_type = next(a for a in args if a is not type(None))

            json_type = PYTHON_TYPE_TO_JSON.get(base_type, "string")
            properties[param_name] = {"type": json_type}

            if param.default is inspect.Parameter.empty and not is_optional:
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def to_claude_format(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.schema,
        }


def register_tool(name: str, description: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        _registry[name] = ToolEntry(name, description, func)
        return func
    return decorator


def get_tool(name: str) -> ToolEntry | None:
    return _registry.get(name)


def get_all_tools() -> list[ToolEntry]:
    return list(_registry.values())


def get_tools_for_claude(enabled_tools: list[str] | None = None) -> list[dict]:
    tools = get_all_tools()
    if enabled_tools is not None:
        tools = [t for t in tools if t.name in enabled_tools]
    return [t.to_claude_format() for t in tools]
