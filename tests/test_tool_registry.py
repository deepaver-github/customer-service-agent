from __future__ import annotations

import app.tools.examples  # noqa: F401
import app.escalation.handler  # noqa: F401
from app.tools.registry import get_tool, get_all_tools, get_tools_for_claude


class TestToolRegistry:
    def test_tools_are_registered(self):
        tools = get_all_tools()
        names = {t.name for t in tools}
        assert "lookup_order" in names
        assert "get_account_info" in names
        assert "search_faq" in names
        assert "escalate" in names

    def test_get_tool_by_name(self):
        tool = get_tool("lookup_order")
        assert tool is not None
        assert tool.name == "lookup_order"

    def test_get_tool_returns_none_for_unknown(self):
        assert get_tool("nonexistent_tool") is None

    def test_tool_schema_generation(self):
        tool = get_tool("lookup_order")
        schema = tool.schema
        assert schema["type"] == "object"
        assert "order_id" in schema["properties"]
        assert "email" in schema["properties"]
        assert schema["required"] == []

    def test_required_params(self):
        tool = get_tool("get_account_info")
        schema = tool.schema
        assert "customer_id" in schema["required"]

    def test_claude_format(self):
        tools = get_tools_for_claude(["lookup_order"])
        assert len(tools) == 1
        t = tools[0]
        assert t["name"] == "lookup_order"
        assert "description" in t
        assert "input_schema" in t

    def test_filter_by_enabled(self):
        all_tools = get_tools_for_claude()
        filtered = get_tools_for_claude(["lookup_order", "escalate"])
        assert len(filtered) == 2
        assert len(all_tools) >= len(filtered)

    def test_tool_execution(self):
        tool = get_tool("lookup_order")
        result = tool.func(order_id="ORD-1234")
        assert result["order_id"] == "ORD-1234"
        assert result["status"] == "shipped"

    def test_tool_execution_not_found(self):
        tool = get_tool("lookup_order")
        result = tool.func(order_id="NONEXISTENT")
        assert "error" in result

    def test_faq_search(self):
        tool = get_tool("search_faq")
        result = tool.func(query="return policy")
        assert len(result["results"]) > 0

    def test_account_info(self):
        tool = get_tool("get_account_info")
        result = tool.func(customer_id="CUST-001")
        assert result["name"] == "Jane Smith"
