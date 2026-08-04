"""offer work mode

Revision ID: dae74d08d7a4
Revises: a6b7c8d9e0f1
Create Date: 2026-08-04 19:02:07.142363

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dae74d08d7a4'
down_revision: Union[str, Sequence[str], None] = 'a6b7c8d9e0f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("offers", sa.Column("work_mode", sa.String(16), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("offers", "work_mode")
