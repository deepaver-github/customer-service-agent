from __future__ import annotations

import pytest
from app.memory import repository as repo
from app.memory.models import SessionStatus


class TestMemory:
    async def test_create_session(self, db):
        session = await repo.create_session(db)
        assert session.id is not None
        assert session.status == SessionStatus.ACTIVE

    async def test_create_session_with_metadata(self, db):
        session = await repo.create_session(db, metadata={"customer_id": "C1"})
        assert session.metadata_ == {"customer_id": "C1"}

    async def test_get_session(self, db):
        session = await repo.create_session(db)
        fetched = await repo.get_session(db, session.id)
        assert fetched is not None
        assert fetched.id == session.id

    async def test_get_session_not_found(self, db):
        result = await repo.get_session(db, "nonexistent-id")
        assert result is None

    async def test_update_session_status(self, db):
        session = await repo.create_session(db)
        updated = await repo.update_session_status(
            db, session.id, SessionStatus.ESCALATED
        )
        assert updated.status == SessionStatus.ESCALATED

    async def test_add_and_get_messages(self, db):
        session = await repo.create_session(db)
        await repo.add_message(db, session.id, "user", "Hello")
        await repo.add_message(db, session.id, "assistant", "Hi there!")

        messages = await repo.get_messages(db, session.id)
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "Hello"
        assert messages[1].role == "assistant"

    async def test_get_messages_with_limit(self, db):
        session = await repo.create_session(db)
        for i in range(5):
            await repo.add_message(db, session.id, "user", f"Message {i}")

        messages = await repo.get_messages(db, session.id, limit=3)
        assert len(messages) == 3

    async def test_get_message_count(self, db):
        session = await repo.create_session(db)
        await repo.add_message(db, session.id, "user", "Hello")
        await repo.add_message(db, session.id, "assistant", "Hi")

        count = await repo.get_message_count(db, session.id)
        assert count == 2
