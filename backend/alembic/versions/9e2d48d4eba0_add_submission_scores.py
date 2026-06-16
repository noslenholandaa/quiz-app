"""add_submission_scores

Revision ID: 9e2d48d4eba0
Revises: 1c7aab303661
Create Date: 2026-06-10 14:04:45.846646

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e2d48d4eba0'
down_revision: Union[str, Sequence[str], None] = '1c7aab303661'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if "submissions" not in tables:
        return
    columns = [c["name"] for c in inspector.get_columns("submissions")]
    if "score" not in columns:
        op.add_column("submissions", sa.Column("score", sa.Integer(), server_default=sa.text("0")))
    if "max_score" not in columns:
        op.add_column("submissions", sa.Column("max_score", sa.Integer(), server_default=sa.text("0")))
    if "percentage" not in columns:
        op.add_column("submissions", sa.Column("percentage", sa.Integer(), server_default=sa.text("0")))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if "submissions" not in tables:
        return
    columns = [c["name"] for c in inspector.get_columns("submissions")]
    if "percentage" in columns:
        op.drop_column("submissions", "percentage")
    if "max_score" in columns:
        op.drop_column("submissions", "max_score")
    if "score" in columns:
        op.drop_column("submissions", "score")
