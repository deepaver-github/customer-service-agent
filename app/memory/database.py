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

AUDITED_TABLES = (
    "participants",
    "contacts",
    "staff",
    "participant_staff_assignments",
    "plans",
    "goals",
    "plan_goals",
    "service_agreements",
    # Phase 3
    "shifts",
    # Phase 4
    "progress_notes",
    "incidents",
    "incident_followups",
    "medication_records",
    "medication_administration_log",
    "restrictive_practices",
    "risk_assessments",
    "documents",
    # Auth
    "users",
)


def _trigger_sql(table: str) -> str:
    return f"""
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = '{table}_audit_trigger') THEN
        CREATE TRIGGER {table}_audit_trigger
        AFTER INSERT OR UPDATE OR DELETE ON {table}
        FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();
    END IF;
END $$
"""


PROGRESS_NOTE_IMMUTABILITY_SQL = """
CREATE OR REPLACE FUNCTION progress_notes_immutability_func()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND OLD.locked_at IS NOT NULL THEN
        RAISE EXCEPTION 'progress_notes.id=% is locked at % and cannot be modified; create a corrects_note_id row instead',
            OLD.id, OLD.locked_at;
    ELSIF TG_OP = 'DELETE' AND OLD.locked_at IS NOT NULL THEN
        RAISE EXCEPTION 'progress_notes.id=% is locked at % and cannot be deleted',
            OLD.id, OLD.locked_at;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
"""

PROGRESS_NOTE_IMMUTABILITY_TRIGGER_SQL = """
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'progress_notes_immutability_trigger') THEN
        CREATE TRIGGER progress_notes_immutability_trigger
        BEFORE UPDATE OR DELETE ON progress_notes
        FOR EACH ROW EXECUTE FUNCTION progress_notes_immutability_func();
    END IF;
END $$
"""

MED_ADMIN_IMMUTABILITY_SQL = """
CREATE OR REPLACE FUNCTION med_admin_immutability_func()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'medication_administration_log rows are immutable (id=%); record a new entry instead',
            OLD.id;
    ELSIF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'medication_administration_log rows are immutable (id=%); record a new entry instead',
            OLD.id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql
"""

MED_ADMIN_IMMUTABILITY_TRIGGER_SQL = """
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'med_admin_immutability_trigger') THEN
        CREATE TRIGGER med_admin_immutability_trigger
        BEFORE UPDATE OR DELETE ON medication_administration_log
        FOR EACH ROW EXECUTE FUNCTION med_admin_immutability_func();
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
            for table in AUDITED_TABLES:
                await conn.execute(text(_trigger_sql(table)))
            await conn.execute(text(PROGRESS_NOTE_IMMUTABILITY_SQL))
            await conn.execute(text(PROGRESS_NOTE_IMMUTABILITY_TRIGGER_SQL))
            await conn.execute(text(MED_ADMIN_IMMUTABILITY_SQL))
            await conn.execute(text(MED_ADMIN_IMMUTABILITY_TRIGGER_SQL))


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Database not initialized — call init_db first")
    return _session_factory


async def get_db() -> AsyncSession:
    if _session_factory is None:
        raise RuntimeError("Database not initialized — call init_db first")
    async with _session_factory() as session:
        yield session
