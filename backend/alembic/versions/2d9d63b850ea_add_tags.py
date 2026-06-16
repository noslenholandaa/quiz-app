"""add_tags

Revision ID: 2d9d63b850ea
Revises: bcd06d104b97
Create Date: 2026-06-10 14:15:18.395141

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d9d63b850ea'
down_revision: Union[str, Sequence[str], None] = 'bcd06d104b97'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if "tags" not in tables:
        op.create_table(
            "tags",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )
        op.create_index(op.f("ix_tags_id"), "tags", ["id"], unique=False)
    if "quiz_tags" not in tables and "quizzes" in tables:
        op.create_table(
            "quiz_tags",
            sa.Column("quiz_id", sa.Integer(), sa.ForeignKey("quizzes.id"), primary_key=True),
            sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id"), primary_key=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if "quiz_tags" in tables:
        op.drop_table("quiz_tags")
    if "tags" in tables:
        op.drop_index(op.f("ix_tags_id"), table_name="tags")
        op.drop_table("tags")
