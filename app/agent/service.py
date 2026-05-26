from __future__ import annotations

import json
from typing import Any, AsyncIterator

import anthropic
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.prompt import build_system_prompt
from app.agent.tool_executor import execute_tool
from app.config import get_settings
from app.escalation.handler import handle_escalation
from app.memory import repository as repo
from app.memory.models import SessionStatus
from app.tools.registry import get_tools_for_claude

log = structlog.get_logger()


class AgentResponse:
    def __init__(
        self,
        session_id: str,
        response: str,
        escalated: bool = False,
        escalation_reason: str | None = None,
        tools_used: list[str] | None = None,
    ):
        self.session_id = session_id
        self.response = response
        self.escalated = escalated
        self.escalation_reason = escalation_reason
        self.tools_used = tools_used or []


class AgentService:
    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        agent_config: dict[str, Any],
    ):
        self.client = client
        self.config = agent_config
        self.model = agent_config.get("model", "claude-sonnet-4-6")
        self.max_tokens = agent_config.get("max_tokens", 1024)
        self.max_tool_iterations = agent_config.get("max_tool_iterations", 10)
        self.enabled_tools = agent_config.get("enabled_tools", [])
        self.system_prompt = build_system_prompt(agent_config)

    async def process_message(
        self,
        db: AsyncSession,
        message: str,
        session_id: str | None = None,
    ) -> AgentResponse:
        if session_id:
            session = await repo.get_session(db, session_id)
            if session is None:
                session = await repo.create_session(db)
        else:
            session = await repo.create_session(db)

        messages = await self._build_messages(db, session.id, message)
        await repo.add_message(db, session.id, "user", message)

        turn_count = await repo.get_message_count(db, session.id)
        max_turns = self.config.get("escalation", {}).get("max_turns_before_escalate", 5)
        force_escalate = turn_count >= max_turns * 2

        tools = get_tools_for_claude(self.enabled_tools)
        tools_used: list[str] = []
        escalated = False
        escalation_reason = None

        if force_escalate:
            escalated = True
            escalation_reason = f"Auto-escalated after {max_turns} turns without resolution"
            tools_used.append("escalate")
            text_response = "I've been unable to fully resolve your issue, so I'm connecting you with a human agent who can help further. Thank you for your patience."
            await repo.add_message(db, session.id, "assistant", text_response)
            await repo.update_session_status(db, session.id, SessionStatus.ESCALATED)
            log.info("auto_escalation", session_id=session.id, turn_count=turn_count)
            return AgentResponse(
                session_id=session.id,
                response=text_response,
                escalated=True,
                escalation_reason=escalation_reason,
                tools_used=tools_used,
            )

        for _ in range(self.max_tool_iterations):
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self.system_prompt,
                messages=messages,
                tools=tools if tools else anthropic.NOT_GIVEN,
            )

            if response.stop_reason == "tool_use":
                assistant_content = response.content
                messages.append({"role": "assistant", "content": assistant_content})

                tool_results = []
                for block in assistant_content:
                    if block.type == "tool_use":
                        if block.name == "escalate":
                            escalated = True
                            escalation_reason = block.input.get("reason", "Customer requested escalation")
                            tools_used.append("escalate")
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps({"status": "escalated", "reason": escalation_reason}),
                            })
                        else:
                            tools_used.append(block.name)
                            result = await execute_tool(block.name, block.input, db=db)
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps(result, default=str),
                            })

                messages.append({"role": "user", "content": tool_results})

                if escalated:
                    response = await self.client.messages.create(
                        model=self.model,
                        max_tokens=self.max_tokens,
                        system=self.system_prompt,
                        messages=messages,
                        tools=tools if tools else anthropic.NOT_GIVEN,
                    )
                    break
            else:
                break

        text_response = self._extract_text(response)
        await repo.add_message(db, session.id, "assistant", text_response)

        if escalated:
            await repo.update_session_status(db, session.id, SessionStatus.ESCALATED)

        log.info(
            "message_processed",
            session_id=session.id,
            tools_used=tools_used,
            escalated=escalated,
        )

        return AgentResponse(
            session_id=session.id,
            response=text_response,
            escalated=escalated,
            escalation_reason=escalation_reason,
            tools_used=tools_used,
        )

    async def process_message_stream(
        self,
        db: AsyncSession,
        message: str,
        session_id: str | None = None,
    ) -> AsyncIterator[dict]:
        if session_id:
            session = await repo.get_session(db, session_id)
            if session is None:
                session = await repo.create_session(db)
        else:
            session = await repo.create_session(db)

        messages = await self._build_messages(db, session.id, message)
        await repo.add_message(db, session.id, "user", message)

        yield {"event": "stream_start", "data": {"session_id": session.id}}

        turn_count = await repo.get_message_count(db, session.id)
        max_turns = self.config.get("escalation", {}).get("max_turns_before_escalate", 5)
        force_escalate = turn_count >= max_turns * 2

        tools = get_tools_for_claude(self.enabled_tools)
        tools_used: list[str] = []
        escalated = False
        escalation_reason = None

        if force_escalate:
            escalated = True
            escalation_reason = f"Auto-escalated after {max_turns} turns without resolution"
            tools_used.append("escalate")
            text_response = "I've been unable to fully resolve your issue, so I'm connecting you with a human agent who can help further. Thank you for your patience."
            await repo.add_message(db, session.id, "assistant", text_response)
            await repo.update_session_status(db, session.id, SessionStatus.ESCALATED)
            yield {"event": "escalation", "data": {"reason": escalation_reason}}
            yield {
                "event": "done",
                "data": {
                    "response": text_response,
                    "session_id": session.id,
                    "escalated": True,
                    "tools_used": tools_used,
                },
            }
            return

        final_text = ""

        try:
            for _ in range(self.max_tool_iterations):
                final_text = ""
                tool_blocks: list[dict] = []
                current_tool_id = None
                current_tool_name = None
                current_tool_input_parts: list[str] = []
                stop_reason = None

                async with self.client.messages.stream(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=self.system_prompt,
                    messages=messages,
                    tools=tools if tools else anthropic.NOT_GIVEN,
                ) as stream:
                    async for event in stream:
                        if event.type == "content_block_start":
                            if event.content_block.type == "tool_use":
                                current_tool_id = event.content_block.id
                                current_tool_name = event.content_block.name
                                current_tool_input_parts = []
                                yield {
                                    "event": "tool_start",
                                    "data": {
                                        "tool_name": current_tool_name,
                                        "tool_use_id": current_tool_id,
                                    },
                                }
                        elif event.type == "content_block_delta":
                            if event.delta.type == "text_delta":
                                final_text += event.delta.text
                                yield {
                                    "event": "text_delta",
                                    "data": {"delta": event.delta.text},
                                }
                            elif event.delta.type == "input_json_delta":
                                current_tool_input_parts.append(event.delta.partial_json)
                        elif event.type == "content_block_stop":
                            if current_tool_name is not None:
                                input_json = "".join(current_tool_input_parts)
                                tool_blocks.append({
                                    "id": current_tool_id,
                                    "name": current_tool_name,
                                    "input": json.loads(input_json) if input_json else {},
                                })
                                current_tool_name = None
                                current_tool_id = None
                                current_tool_input_parts = []
                        elif event.type == "message_delta":
                            stop_reason = event.delta.stop_reason

                    full_message = await stream.get_final_message()

                if stop_reason == "tool_use":
                    messages.append({"role": "assistant", "content": full_message.content})

                    tool_results = []
                    for tb in tool_blocks:
                        if tb["name"] == "escalate":
                            escalated = True
                            escalation_reason = tb["input"].get("reason", "Customer requested escalation")
                            tools_used.append("escalate")
                            yield {"event": "escalation", "data": {"reason": escalation_reason}}
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tb["id"],
                                "content": json.dumps({"status": "escalated", "reason": escalation_reason}),
                            })
                        else:
                            tools_used.append(tb["name"])
                            result = await execute_tool(tb["name"], tb["input"], db=db)
                            yield {
                                "event": "tool_result",
                                "data": {
                                    "tool_name": tb["name"],
                                    "tool_use_id": tb["id"],
                                    "result": result,
                                },
                            }
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tb["id"],
                                "content": json.dumps(result, default=str),
                            })

                    messages.append({"role": "user", "content": tool_results})
                else:
                    break

        except Exception as exc:
            log.error("stream_error", error=str(exc))
            yield {"event": "error", "data": {"error": str(exc)}}
            return

        await repo.add_message(db, session.id, "assistant", final_text)

        if escalated:
            await repo.update_session_status(db, session.id, SessionStatus.ESCALATED)
            settings = get_settings()
            await handle_escalation(
                db=db,
                session_id=session.id,
                reason=escalation_reason or "Unknown",
                webhook_url=settings.escalation_webhook_url,
            )

        log.info(
            "stream_completed",
            session_id=session.id,
            tools_used=tools_used,
            escalated=escalated,
        )

        yield {
            "event": "done",
            "data": {
                "response": final_text,
                "session_id": session.id,
                "escalated": escalated,
                "tools_used": tools_used,
            },
        }

    async def _build_messages(
        self, db: AsyncSession, session_id: str, new_message: str
    ) -> list[dict]:
        stored = await repo.get_messages(db, session_id)
        messages = []
        max_recent = self.config.get("memory", {}).get("max_recent_messages", 40)

        for msg in stored[-max_recent:]:
            messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": new_message})
        return messages

    @staticmethod
    def _extract_text(response) -> str:
        parts = []
        for block in response.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "\n".join(parts) if parts else ""
