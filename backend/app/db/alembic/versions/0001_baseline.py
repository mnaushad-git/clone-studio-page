"""baseline

Establishes the Alembic migration history for the project. No business tables
exist yet in Phase 1 (Backend Foundation) — this revision intentionally creates
nothing beyond what `alembic upgrade head` itself manages (the `alembic_version`
table), per docs/architecture/implementation-roadmap.md step 1/2.

Revision ID: 0001
Revises:
Create Date: 2026-07-27

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
