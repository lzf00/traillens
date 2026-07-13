"""perf indexes: photos(trail_id, created_at) + trails(user_id, updated_at DESC)

Revision ID: 20260713_0005
Revises: 20260701_0004
Create Date: 2026-07-13

P1 audit 建议:补复合索引让 list_trails ORDER BY updated_at DESC 与
list_photos ORDER BY created_at 走 index-only scan。
"""

from alembic import op


revision = "20260713_0005"
down_revision = "20260701_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # photos(trail_id, created_at) — 按 trail 列 photos + 创建时序时用
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_photos_trail_created
        ON photos(trail_id, created_at)
    """)
    # trails(user_id, updated_at DESC) — list_trails ORDER BY updated_at DESC
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_trails_user_updated
        ON trails(user_id, updated_at DESC)
    """)
    # photos(trail_id, verdict) — 拉 keeps.zip 时按 verdict='keep' 过滤
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_photos_trail_verdict
        ON photos(trail_id, verdict)
        WHERE verdict IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_photos_trail_created")
    op.execute("DROP INDEX IF EXISTS idx_trails_user_updated")
    op.execute("DROP INDEX IF EXISTS idx_photos_trail_verdict")
