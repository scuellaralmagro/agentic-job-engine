"""add contact block to the profile

Revision ID: d3a4b5c6e7f8
Revises: c2a3b4d5e6f7
Create Date: 2026-08-03 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d3a4b5c6e7f8"
down_revision: Union[str, Sequence[str], None] = "c2a3b4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("profile", sa.Column("contact", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("profile", "contact")
