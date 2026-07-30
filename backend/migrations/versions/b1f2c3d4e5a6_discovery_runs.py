"""add offers.posted_at and discovery_runs

Revision ID: b1f2c3d4e5a6
Revises: 3e04d2690646
Create Date: 2026-07-30 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b1f2c3d4e5a6"
down_revision: Union[str, Sequence[str], None] = "3e04d2690646"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("offers", sa.Column("posted_at", sa.DateTime(), nullable=True))
    op.create_table(
        "discovery_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("saved_search_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("offers_found", sa.Integer(), nullable=False),
        sa.Column("offers_new", sa.Integer(), nullable=False),
        sa.Column("source_results", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["saved_search_id"], ["saved_searches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("discovery_runs")
    op.drop_column("offers", "posted_at")
