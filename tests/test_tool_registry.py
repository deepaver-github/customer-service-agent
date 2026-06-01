from __future__ import annotations

import app.tools.examples  # noqa: F401
import app.escalation.handler  # noqa: F401
from app.tools.registry import get_tool, get_all_tools, get_tools_for_claude


class TestToolRegistry:
    def test_tools_are_registered(self):
        tools = get_all_tools()
        names = {t.name for t in tools}
        assert "lookup_participant" in names
        assert "get_contacts" in names
        assert "search_knowledge" in names
        assert "escalate" in names

    def test_get_tool_by_name(self):
        tool = get_tool("lookup_participant")
        assert tool is not None
        assert tool.name == "lookup_participant"

    def test_get_tool_returns_none_for_unknown(self):
        assert get_tool("nonexistent_tool") is None

    def test_lookup_participant_schema(self):
        tool = get_tool("lookup_participant")
        schema = tool.schema
        assert schema["type"] == "object"
        assert "ndis_number" in schema["properties"]
        assert "name_or_email" in schema["properties"]
        assert schema["required"] == []

    def test_get_contacts_requires_participant_id(self):
        tool = get_tool("get_contacts")
        schema = tool.schema
        assert "participant_id" in schema["required"]

    def test_search_knowledge_requires_query(self):
        tool = get_tool("search_knowledge")
        schema = tool.schema
        assert "query" in schema["required"]

    def test_claude_format(self):
        tools = get_tools_for_claude(["lookup_participant"])
        assert len(tools) == 1
        t = tools[0]
        assert t["name"] == "lookup_participant"
        assert "description" in t
        assert "input_schema" in t

    def test_filter_by_enabled(self):
        all_tools = get_tools_for_claude()
        filtered = get_tools_for_claude(["lookup_participant", "escalate"])
        assert len(filtered) == 2
        assert len(all_tools) >= len(filtered)


class TestParticipantTools:
    """Execution tests for the new NDIS tools against the in-memory test DB."""

    async def test_lookup_participant_requires_input(self, db):
        from app.tools.examples.lookup_participant import lookup_participant

        result = await lookup_participant(db=db)
        assert "error" in result

    async def test_lookup_participant_not_found(self, db):
        from app.tools.examples.lookup_participant import lookup_participant

        result = await lookup_participant(db=db, ndis_number="999000000")
        assert "error" in result

    async def test_lookup_participant_finds_by_ndis_number(self, db):
        from app.memory.models import Participant, ParticipantStatus
        from app.tools.examples.lookup_participant import lookup_participant

        p = Participant(
            ndis_number="430000001",
            first_name="Test",
            last_name="User",
            status=ParticipantStatus.ACTIVE,
        )
        db.add(p)
        await db.commit()

        result = await lookup_participant(db=db, ndis_number="430000001")
        assert result["match"] == "single"
        assert result["participant"]["first_name"] == "Test"
        assert result["participant"]["last_name"] == "User"

    async def test_lookup_participant_finds_by_name(self, db):
        from app.memory.models import Participant, ParticipantStatus
        from app.tools.examples.lookup_participant import lookup_participant

        p = Participant(
            ndis_number="430000002",
            first_name="Aisha",
            last_name="Patel",
            status=ParticipantStatus.ACTIVE,
        )
        db.add(p)
        await db.commit()

        result = await lookup_participant(db=db, name_or_email="aisha")
        assert result["match"] == "single"
        assert result["participant"]["last_name"] == "Patel"

    async def test_get_contacts_unknown_participant(self, db):
        from app.tools.examples.get_contacts import get_contacts

        result = await get_contacts(db=db, participant_id="does-not-exist")
        assert "error" in result

    async def test_get_contacts_returns_primary_first(self, db):
        from app.memory.models import (
            Contact,
            ContactRelationship,
            Participant,
            ParticipantStatus,
        )
        from app.tools.examples.get_contacts import get_contacts

        p = Participant(
            ndis_number="430000003",
            first_name="X",
            last_name="Y",
            status=ParticipantStatus.ACTIVE,
        )
        db.add(p)
        await db.commit()
        db.add(
            Contact(
                participant_id=p.id,
                name="Secondary",
                relationship_type=ContactRelationship.GP,
                is_primary=False,
                is_emergency=False,
            )
        )
        db.add(
            Contact(
                participant_id=p.id,
                name="Primary Person",
                relationship_type=ContactRelationship.FAMILY,
                is_primary=True,
                is_emergency=True,
            )
        )
        await db.commit()

        result = await get_contacts(db=db, participant_id=p.id)
        assert result["contacts"][0]["name"] == "Primary Person"
        assert result["contacts"][0]["is_primary"] is True

    async def test_search_knowledge_empty(self, db):
        from app.tools.examples.search_knowledge import search_knowledge

        result = await search_knowledge(db=db, query="anything")
        assert result["results"] == []

    async def test_search_knowledge_matches_published(self, db):
        from app.memory.models import (
            KnowledgeArticle,
            KnowledgeCategory,
            KnowledgeStatus,
        )
        from app.tools.examples.search_knowledge import search_knowledge

        db.add(
            KnowledgeArticle(
                title="Supported Independent Living explained",
                body_md="SIL helps you live independently.",
                category=KnowledgeCategory.SUPPORTS_EXPLAINED,
                status=KnowledgeStatus.PUBLISHED,
            )
        )
        db.add(
            KnowledgeArticle(
                title="Draft article",
                body_md="independent independent independent",
                category=KnowledgeCategory.OTHER,
                status=KnowledgeStatus.DRAFT,
            )
        )
        await db.commit()

        result = await search_knowledge(db=db, query="independent")
        titles = [r["title"] for r in result["results"]]
        assert "Supported Independent Living explained" in titles
        assert "Draft article" not in titles
