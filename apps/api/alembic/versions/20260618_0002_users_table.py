"""users table for real auth.

- bcrypt 密码哈希
- email 全小写唯一
- 兼容现有 trails.user_id(uuid 类型)

Revision ID: 20260618_0002
Revises: 20260526_0001
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260618_0002"
down_revision: Union[str, None] = "20260526_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
            email           text NOT NULL UNIQUE,
            password_hash   text,                 -- NULL → 仅邮箱登录(magic)
            name            text,
            plan            text NOT NULL DEFAULT 'free',
            quota_remaining int  NOT NULL DEFAULT 50,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(lower(email));
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS users CASCADE;")
