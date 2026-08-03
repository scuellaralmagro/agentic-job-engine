"""add embeddings table and match scoring columns

Revision ID: c2a3b4d5e6f7
Revises: b1f2c3d4e5a6
Create Date: 2026-08-03 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c2a3b4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "b1f2c3d4e5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "embeddings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_kind", sa.String(length=32), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("item_key", sa.String(length=255), nullable=False),
        sa.Column("text_hash", sa.String(length=64), nullable=False),
        sa.Column("dim", sa.Integer(), nullable=False),
        sa.Column("vector", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_kind", "owner_id", "item_key", name="uq_embeddings_owner_item"
        ),
    )
    op.create_index("ix_embeddings_owner", "embeddings", ["owner_kind", "owner_id"])

    # SQLite cannot ALTER in constraints, so alembic rebuilds the table for us
    with op.batch_alter_table("matches") as batch:
        batch.add_column(
            sa.Column("status", sa.String(length=16), nullable=False, server_default="new")
        )
        batch.add_column(
            sa.Column(
                "scored_by", sa.String(length=16), nullable=False, server_default="rubric"
            )
        )
        batch.add_column(sa.Column("similarity", sa.Float(), nullable=True))
        batch.add_column(sa.Column("scored_at", sa.DateTime(), nullable=True))
        batch.create_unique_constraint(
            "uq_matches_offer_profile", ["offer_id", "profile_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("matches") as batch:
        batch.drop_constraint("uq_matches_offer_profile", type_="unique")
        batch.drop_column("scored_at")
        batch.drop_column("similarity")
        batch.drop_column("scored_by")
        batch.drop_column("status")
    op.drop_index("ix_embeddings_owner", table_name="embeddings")
    op.drop_table("embeddings")
