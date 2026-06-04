from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.memory import repository as repo
from app.memory.repository import (
    _decode_cursor,
    _encode_cursor,
    _extract_preview,
)


# Repo-level test owner. list_sessions requires an explicit scope, so every
# test in this file stamps and queries against the same synthetic user.
FAKE_USER_ID = "00000000-0000-0000-0000-000000000001"


async def _make_session_at(db, when: datetime):
    """Create a session and force its updated_at to `when` (for deterministic order)."""
    session = await repo.create_session(db, user_id=FAKE_USER_ID)
    session.updated_at = when
    session.created_at = when
    await db.commit()
    await db.refresh(session)
    return session


class TestExtractPreview:
    def test_string(self):
        assert _extract_preview("Hello there") == "Hello there"

    def test_none(self):
        assert _extract_preview(None) is None

    def test_text_block_list(self):
        content = [{"type": "text", "text": "Sure, here's your answer."}]
        assert _extract_preview(content) == "Sure, here's your answer."

    def test_tool_use_list(self):
        content = [{"type": "tool_use", "name": "lookup_participant", "input": {}}]
        assert _extract_preview(content) == "[used lookup_participant]"

    def test_mixed_text_and_tool_use(self):
        content = [
            {"type": "text", "text": "Looking that up."},
            {"type": "tool_use", "name": "lookup_participant"},
        ]
        assert _extract_preview(content) == "Looking that up. [used lookup_participant]"

    def test_tool_result_list(self):
        content = [{"type": "tool_result", "tool_use_id": "x", "content": "ok"}]
        assert _extract_preview(content) == "[tool result]"

    def test_dict_with_text(self):
        assert _extract_preview({"text": "Hi"}) == "Hi"

    def test_dict_tool_use(self):
        assert _extract_preview({"type": "tool_use", "name": "faq_search"}) == "[used faq_search]"

    def test_truncation(self):
        long = "a" * 200
        result = _extract_preview(long)
        assert result is not None
        assert len(result) <= 120
        assert result.endswith("…")

    def test_whitespace_normalized(self):
        assert _extract_preview("Hello\n\n\nworld   tabs\there") == "Hello world tabs here"

    def test_empty_list_returns_none(self):
        assert _extract_preview([]) is None

    def test_unrecognized_dict_returns_none(self):
        assert _extract_preview({"foo": "bar"}) is None


class TestCursorCodec:
    def test_roundtrip(self):
        when = datetime(2026, 5, 31, 12, 34, 56, tzinfo=timezone.utc)
        sid = "abc-123"
        encoded = _encode_cursor(when, sid)
        decoded_when, decoded_sid = _decode_cursor(encoded)
        assert decoded_when == when
        assert decoded_sid == sid

    def test_invalid_cursor_raises(self):
        with pytest.raises(ValueError):
            _decode_cursor("not-a-valid-cursor!!!")


class TestListSessions:
    async def test_empty_db(self, db):
        items, next_cursor = await repo.list_sessions(db, user_id=FAKE_USER_ID)
        assert items == []
        assert next_cursor is None

    async def test_single_session_no_messages(self, db):
        session = await repo.create_session(db, user_id=FAKE_USER_ID)
        items, next_cursor = await repo.list_sessions(db, user_id=FAKE_USER_ID)
        assert len(items) == 1
        assert items[0]["id"] == session.id
        assert items[0]["status"] == "active"
        assert items[0]["last_message_preview"] is None
        assert items[0]["message_count"] == 0
        assert next_cursor is None

    async def test_orders_by_updated_at_desc(self, db):
        base = datetime(2026, 5, 31, 10, 0, 0, tzinfo=timezone.utc)
        s_old = await _make_session_at(db, base)
        s_mid = await _make_session_at(db, base + timedelta(minutes=10))
        s_new = await _make_session_at(db, base + timedelta(minutes=20))

        items, _ = await repo.list_sessions(db, user_id=FAKE_USER_ID)
        ids = [item["id"] for item in items]
        assert ids == [s_new.id, s_mid.id, s_old.id]

    async def test_preview_uses_latest_user_or_assistant_message(self, db):
        session = await repo.create_session(db, user_id=FAKE_USER_ID)
        await repo.add_message(db, session.id, "user", "First user message")
        await repo.add_message(db, session.id, "assistant", "Assistant reply")
        await repo.add_message(db, session.id, "tool", [{"type": "tool_result", "content": "ok"}])

        items, _ = await repo.list_sessions(db, user_id=FAKE_USER_ID)
        assert items[0]["last_message_preview"] == "Assistant reply"
        assert items[0]["message_count"] == 3

    async def test_preview_handles_structured_content(self, db):
        session = await repo.create_session(db, user_id=FAKE_USER_ID)
        await repo.add_message(
            db,
            session.id,
            "assistant",
            [{"type": "text", "text": "Found participant."}, {"type": "tool_use", "name": "lookup_participant"}],
        )
        items, _ = await repo.list_sessions(db, user_id=FAKE_USER_ID)
        assert items[0]["last_message_preview"] == "Found participant. [used lookup_participant]"

    async def test_pagination_round_trip(self, db):
        base = datetime(2026, 5, 31, 10, 0, 0, tzinfo=timezone.utc)
        created = [
            await _make_session_at(db, base + timedelta(minutes=i))
            for i in range(5)
        ]
        expected_order = [s.id for s in reversed(created)]

        page1, cursor1 = await repo.list_sessions(db, user_id=FAKE_USER_ID, limit=2)
        assert [it["id"] for it in page1] == expected_order[:2]
        assert cursor1 is not None

        page2, cursor2 = await repo.list_sessions(db, user_id=FAKE_USER_ID, cursor=cursor1, limit=2)
        assert [it["id"] for it in page2] == expected_order[2:4]
        assert cursor2 is not None

        page3, cursor3 = await repo.list_sessions(db, user_id=FAKE_USER_ID, cursor=cursor2, limit=2)
        assert [it["id"] for it in page3] == expected_order[4:]
        assert cursor3 is None

    async def test_invalid_cursor_raises_value_error(self, db):
        with pytest.raises(ValueError):
            await repo.list_sessions(db, user_id=FAKE_USER_ID, cursor="garbage")

    async def test_scope_filters_to_owner(self, db):
        other = "00000000-0000-0000-0000-000000000099"
        mine = await repo.create_session(db, user_id=FAKE_USER_ID)
        await repo.create_session(db, user_id=other)
        items, _ = await repo.list_sessions(db, user_id=FAKE_USER_ID)
        assert [i["id"] for i in items] == [mine.id]

    async def test_admin_view_includes_escalated_across_users(self, db):
        from app.memory.models import SessionStatus
        other = "00000000-0000-0000-0000-000000000099"
        mine = await repo.create_session(db, user_id=FAKE_USER_ID)
        other_escalated = await repo.create_session(db, user_id=other)
        await repo.update_session_status(db, other_escalated.id, SessionStatus.ESCALATED)
        # Other private (non-escalated) session must not leak in.
        await repo.create_session(db, user_id=other)

        items, _ = await repo.list_sessions(
            db, user_id=FAKE_USER_ID, include_escalated=True
        )
        returned = {i["id"] for i in items}
        assert mine.id in returned
        assert other_escalated.id in returned
        assert len(returned) == 2

    async def test_no_n_plus_one(self, db, monkeypatch):
        """Sanity check: listing N sessions should run exactly one execute() call."""
        # 5 sessions with messages
        for _ in range(5):
            session = await repo.create_session(db, user_id=FAKE_USER_ID)
            await repo.add_message(db, session.id, "user", "hello")

        from sqlalchemy.ext.asyncio import AsyncSession as RealAsyncSession

        original_execute = RealAsyncSession.execute
        call_count = {"n": 0}

        async def counting_execute(self, *args, **kwargs):
            call_count["n"] += 1
            return await original_execute(self, *args, **kwargs)

        monkeypatch.setattr(RealAsyncSession, "execute", counting_execute)

        items, _ = await repo.list_sessions(db, user_id=FAKE_USER_ID, limit=20)
        assert len(items) == 5
        assert call_count["n"] == 1, f"expected 1 query, got {call_count['n']} (N+1 regression)"
