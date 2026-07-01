"""add resource_type / item_type for AgentSaaS template abstraction

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-01

Direction C Phase 1: 把 trails 概念抽象为 resource,photos 抽象为 item。
- trails.resource_type: 'trail'(TrailLens 默认) / 'stack'(stargazer) / 'session'(recipe-helper) ...
- photos.item_type: 'photo' / 'dish' / 'stack_frame' ...

字段有默认值,现有数据完全兼容;新 example 用不同值。
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE trails
        ADD COLUMN IF NOT EXISTS resource_type text NOT NULL DEFAULT 'trail';

        CREATE INDEX IF NOT EXISTS idx_trails_resource_type
            ON trails(resource_type);
    """)
    op.execute("""
        ALTER TABLE photos
        ADD COLUMN IF NOT EXISTS item_type text NOT NULL DEFAULT 'photo';
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_trails_resource_type;")
    op.execute("ALTER TABLE trails DROP COLUMN IF EXISTS resource_type;")
    op.execute("ALTER TABLE photos DROP COLUMN IF EXISTS item_type;")
