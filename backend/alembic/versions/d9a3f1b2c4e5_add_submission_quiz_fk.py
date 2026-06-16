"""add_submission_quiz_fk

Revision ID: d9a3f1b2c4e5
Revises: c10f3eee736c
Create Date: 2026-06-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9a3f1b2c4e5"
down_revision: Union[str, Sequence[str], None] = "c10f3eee736c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if "submissions" not in tables:
        return
    dialect = conn.dialect.name
    if dialect == "postgresql":
        existing_fks = [fk["name"] for fk in inspector.get_foreign_keys("submissions")]
        if "fk_submissions_quiz_id" not in existing_fks:
            op.create_foreign_key(
                "fk_submissions_quiz_id",
                "submissions",
                "quizzes",
                ["quiz_id"],
                ["id"],
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if "submissions" not in tables:
        return
    dialect = conn.dialect.name
    if dialect == "postgresql":
        existing_fks = [fk["name"] for fk in inspector.get_foreign_keys("submissions")]
        if "fk_submissions_quiz_id" in existing_fks:
            op.drop_constraint("fk_submissions_quiz_id", "submissions", type_="foreignkey")
