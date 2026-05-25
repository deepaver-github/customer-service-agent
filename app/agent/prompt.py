from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_system_prompt(agent_config: dict[str, Any]) -> str:
    personality = agent_config.get("personality", "You are a helpful customer service agent.")
    max_turns = agent_config.get("escalation", {}).get("max_turns_before_escalate", 5)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""{personality.strip()}

Current date and time: {now}

## Escalation Guidelines
- If the customer explicitly asks to speak with a human agent, use the escalate tool immediately.
- If you detect the customer is very frustrated or angry and you cannot resolve their issue, use the escalate tool.
- If you have been unable to resolve the issue after {max_turns} exchanges, use the escalate tool.
- When escalating, provide a clear reason so the human agent has context.

## Tool Usage
- Use the available tools to look up real information before answering questions about orders, accounts, or policies.
- Never fabricate order numbers, tracking numbers, or account details.
- If a tool returns an error, let the customer know you couldn't find the information and offer alternatives."""
