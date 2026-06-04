"""baseline — snapshot of the schema after Phase 4

This revision is intentionally a no-op. The application's init_db()
currently uses SQLAlchemy's Base.metadata.create_all to bring the
database to the current model state on startup. This baseline lets
Alembic recognise that state as the head revision; future schema
changes should be authored as new revisions on top.

Stamp a fresh database with::

    alembic stamp head

Revision ID: 0001_baseline
Revises:
Create Date: 2026-06-03

"""
from typing import Sequence, Union

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
