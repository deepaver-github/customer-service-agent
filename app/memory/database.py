from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None

AUDIT_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (id, table_name, record_id, action, old_values, new_values, changed_at)
        VALUES (gen_random_uuid()::text, TG_TABLE_NAME, NEW.id, 'INSERT', NULL, row_to_json(NEW), now());
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (id, table_name, record_id, action, old_values, new_values, changed_at)
        VALUES (gen_random_uuid()::text, TG_TABLE_NAME, NEW.id, 'UPDATE', row_to_json(OLD), row_to_json(NEW), now());
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (id, table_name, record_id, action, old_values, new_values, changed_at)
        VALUES (gen_random_uuid()::text, TG_TABLE_NAME, OLD.id, 'DELETE', row_to_json(OLD), NULL, now());
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql
"""

ORDERS_TRIGGER_SQL = """
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'orders_audit_trigger') THEN
        CREATE TRIGGER orders_audit_trigger
        AFTER INSERT OR UPDATE OR DELETE ON orders
        FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();
    END IF;
END $$
"""

ACCOUNTS_TRIGGER_SQL = """
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'accounts_audit_trigger') THEN
        CREATE TRIGGER accounts_audit_trigger
        AFTER INSERT OR UPDATE OR DELETE ON accounts
        FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();
    END IF;
END $$
"""


async def init_db(database_url: str) -> None:
    global _engine, _session_factory
    _engine = create_async_engine(database_url, echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    from app.memory.models import Base
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        if "postgresql" in database_url:
            await conn.execute(text(AUDIT_FUNCTION_SQL))
            await conn.execute(text(ORDERS_TRIGGER_SQL))
            await conn.execute(text(ACCOUNTS_TRIGGER_SQL))


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Database not initialized — call init_db first")
    return _session_factory


async def get_db() -> AsyncSession:
    if _session_factory is None:
        raise RuntimeError("Database not initialized — call init_db first")
    async with _session_factory() as session:
        yield session
