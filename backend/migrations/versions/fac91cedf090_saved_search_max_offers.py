"""saved search max offers

Revision ID: fac91cedf090
Revises: dae74d08d7a4
Create Date: 2026-08-15 16:06:46.614317

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fac91cedf090'
down_revision: Union[str, Sequence[str], None] = 'dae74d08d7a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "saved_searches", sa.Column("max_offers", sa.Integer(), nullable=True)
    )
    # Backfill rather than leaving NULL: a row that predates the column cannot have
    # chosen to be uncapped, and leaving it NULL keeps the spend leak open.
    op.execute("UPDATE saved_searches SET max_offers = 25 WHERE max_offers IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("saved_searches", "max_offers")
