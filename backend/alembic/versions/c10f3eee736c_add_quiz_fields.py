"""add_quiz_fields

Revision ID: c10f3eee736c
Revises: 2d9d63b850ea
Create Date: 2026-06-10 14:15:20.419905

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c10f3eee736c'
down_revision: Union[str, Sequence[str], None] = '2d9d63b850ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if "quizzes" not in tables:
        return
    columns = [c["name"] for c in inspector.get_columns("quizzes")]
    if "category_id" not in columns:
        op.add_column("quizzes", sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True))
    if "views" not in columns:
        op.add_column("quizzes", sa.Column("views", sa.Integer(), server_default=sa.text("0")))
    op.create_index(op.f("ix_quizzes_title"), "quizzes", ["title"], unique=False)
    op.create_index(op.f("ix_quizzes_category_id"), "quizzes", ["category_id"], unique=False)
    op.create_index(op.f("ix_quizzes_views"), "quizzes", ["views"], unique=False)
    op.create_index(op.f("ix_quizzes_created_at"), "quizzes", ["created_at"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if "quizzes" not in tables:
        return
    columns = [c["name"] for c in inspector.get_columns("quizzes")]
    op.drop_index(op.f("ix_quizzes_created_at"), table_name="quizzes")
    op.drop_index(op.f("ix_quizzes_views"), table_name="quizzes")
    op.drop_index(op.f("ix_quizzes_category_id"), table_name="quizzes")
    op.drop_index(op.f("ix_quizzes_title"), table_name="quizzes")
    if "views" in columns:
        op.drop_column("quizzes", "views")
    if "category_id" in columns:
        op.drop_column("quizzes", "category_id")
