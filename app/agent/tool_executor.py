from __future__ import annotations

import structlog
from typing import Any

from app.tools.registry import get_tool

log = structlog.get_logger()


async def execute_tool(tool_name: str, tool_input: dict[str, Any]) -> Any:
    entry = get_tool(tool_name)
    if entry is None:
        log.warning("tool_not_found", tool_name=tool_name)
        return {"error": f"Tool '{tool_name}' not found"}

    try:
        result = entry.func(**tool_input)
        log.info("tool_executed", tool_name=tool_name)
        return result
    except Exception as exc:
        log.error("tool_execution_failed", tool_name=tool_name, error=str(exc))
        return {"error": f"Tool execution failed: {str(exc)}"}
