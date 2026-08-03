"""add discovery_results and run query columns

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-08-03 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a6b7c8d9e0f1"
down_revision: Union[str, Sequence[str], None] = "f5a6b7c8d9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing runs predate ad-hoc search: they were all scheduled or run-now against
    # a saved search, and their query is not recoverable.
    op.add_column(
        "discovery_runs",
        sa.Column(
            "kind", sa.String(length=16), nullable=False, server_default="scheduled"
        ),
    )
    op.add_column("discovery_runs", sa.Column("term", sa.Text(), nullable=True))
    op.add_column("discovery_runs", sa.Column("filters", sa.JSON(), nullable=True))

    op.create_table(
        "discovery_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("offer_id", sa.Integer(), nullable=False),
        sa.Column("is_new", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["discovery_runs.id"]),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "offer_id", name="uq_discovery_results_run_offer"),
    )
    op.create_index("ix_discovery_results_run_id", "discovery_results", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_discovery_results_run_id", table_name="discovery_results")
    op.drop_table("discovery_results")
    op.drop_column("discovery_runs", "filters")
    op.drop_column("discovery_runs", "term")
    op.drop_column("discovery_runs", "kind")
