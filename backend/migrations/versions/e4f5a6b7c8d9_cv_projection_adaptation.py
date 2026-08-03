"""add adaptation columns to cv_projections

Revision ID: e4f5a6b7c8d9
Revises: d3a4b5c6e7f8
Create Date: 2026-08-03 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "d3a4b5c6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("cv_projections") as batch:
        batch.add_column(sa.Column("match_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("suggestions", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("language", sa.String(length=8), nullable=True))
        batch.create_foreign_key(
            "fk_cv_projections_match", "matches", ["match_id"], ["id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("cv_projections") as batch:
        batch.drop_constraint("fk_cv_projections_match", type_="foreignkey")
        batch.drop_column("language")
        batch.drop_column("suggestions")
        batch.drop_column("match_id")
