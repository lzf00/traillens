"""photos.thumb_uri 字段:300px 缩略图 URL,列表加载快。

Revision ID: 0003
Revises: 0002
"""

from __future__ import annotations
from typing import Sequence, Union
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE photos ADD COLUMN IF NOT EXISTS thumb_uri text;")


def downgrade() -> None:
    op.execute("ALTER TABLE photos DROP COLUMN IF EXISTS thumb_uri;")
