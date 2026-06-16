"""add_performance_indexes

Revision ID: e5f4a6b7c8d9
Revises: d9a3f1b2c4e5
Create Date: 2026-06-12 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f4a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "d9a3f1b2c4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    for tbl in ("submissions", "quizzes", "users", "refresh_tokens", "password_reset_tokens", "categories", "tags"):
        if tbl not in tables:
            return

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("submissions")}
    existing_users = {idx["name"] for idx in inspector.get_indexes("users")}
    existing_rt = {idx["name"] for idx in inspector.get_indexes("refresh_tokens")}
    existing_prt = {idx["name"] for idx in inspector.get_indexes("password_reset_tokens")}

    if "ix_submissions_user_id" not in existing_indexes:
        op.create_index("ix_submissions_user_id", "submissions", ["user_id"])
    if "ix_submissions_quiz_id" not in existing_indexes:
        op.create_index("ix_submissions_quiz_id", "submissions", ["quiz_id"])
    if "ix_submissions_created_at" not in existing_indexes:
        op.create_index("ix_submissions_created_at", "submissions", ["created_at"])
    if "ix_submissions_percentage" not in existing_indexes:
        op.create_index("ix_submissions_percentage", "submissions", ["percentage"])

    if "ix_users_role" not in existing_users:
        op.create_index("ix_users_role", "users", ["role"])

    if "ix_refresh_tokens_expires_at" not in existing_rt:
        op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])

    if "ix_password_reset_tokens_expires_at" not in existing_prt:
        op.create_index("ix_password_reset_tokens_expires_at", "password_reset_tokens", ["expires_at"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    for tbl in ("submissions", "quizzes", "users", "refresh_tokens", "password_reset_tokens", "categories", "tags"):
        if tbl not in tables:
            return

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("submissions")}
    existing_users = {idx["name"] for idx in inspector.get_indexes("users")}
    existing_rt = {idx["name"] for idx in inspector.get_indexes("refresh_tokens")}
    existing_prt = {idx["name"] for idx in inspector.get_indexes("password_reset_tokens")}

    if "ix_submissions_user_id" in existing_indexes:
        op.drop_index("ix_submissions_user_id", "submissions")
    if "ix_submissions_quiz_id" in existing_indexes:
        op.drop_index("ix_submissions_quiz_id", "submissions")
    if "ix_submissions_created_at" in existing_indexes:
        op.drop_index("ix_submissions_created_at", "submissions")
    if "ix_submissions_percentage" in existing_indexes:
        op.drop_index("ix_submissions_percentage", "submissions")

    if "ix_users_role" in existing_users:
        op.drop_index("ix_users_role", "users")

    if "ix_refresh_tokens_expires_at" in existing_rt:
        op.drop_index("ix_refresh_tokens_expires_at", "refresh_tokens")

    if "ix_password_reset_tokens_expires_at" in existing_prt:
        op.drop_index("ix_password_reset_tokens_expires_at", "password_reset_tokens")
