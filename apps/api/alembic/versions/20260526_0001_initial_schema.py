"""initial schema: trails / photos / user_preferences / agent_runs / subscriptions

Revision ID: 0001
Revises:
Create Date: 2026-05-26

落地 docs/PRODUCT_PLAN.md §4.2 的 5 张表。
扩展 (vector, postgis, uuid-ossp) 由 docker-compose 的 init script 创建,
此处只创建表与索引。
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- 扩展(每次启动 init script 可能没跑,这里幂等装一次) -----------
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute('CREATE EXTENSION IF NOT EXISTS vector;')

    # ---- subscriptions ---------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id              uuid PRIMARY KEY,
            stripe_customer_id   text UNIQUE,
            plan                 text NOT NULL DEFAULT 'free',
            quota_monthly        int  NOT NULL DEFAULT 50,
            current_period_end   timestamptz,
            created_at           timestamptz NOT NULL DEFAULT now(),
            updated_at           timestamptz NOT NULL DEFAULT now()
        );
        """
    )

    # ---- trails ----------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS trails (
            id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id         uuid NOT NULL,
            name            text NOT NULL,
            location_name   text,
            gpx_uri         text,
            -- gps_bbox 用 jsonb 存 {lat_min,lat_max,lon_min,lon_max}
            -- (MVP 不上 PostGIS;以后做空间检索时改 geometry+GIST)
            gps_bbox        jsonb,
            state           jsonb NOT NULL DEFAULT '{}'::jsonb,
            travelogue_md   text,
            next_trip_plan  jsonb,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_trails_user ON trails(user_id);
        """
    )

    # ---- photos ----------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS photos (
            id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
            trail_id        uuid NOT NULL REFERENCES trails(id) ON DELETE CASCADE,
            uri             text NOT NULL,
            exif            jsonb,
            verdict         text,
            reject_reason   text,
            aesthetic       jsonb,
            critique        text,
            embedding       vector(768),
            decision_trace  jsonb NOT NULL DEFAULT '[]'::jsonb,
            created_at      timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_photos_trail ON photos(trail_id);
        -- pgvector cosine 索引:embedding 写入后批量 REINDEX
        CREATE INDEX IF NOT EXISTS idx_photos_emb
          ON photos USING ivfflat (embedding vector_cosine_ops);
        """
    )

    # ---- user_preferences -------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id                uuid PRIMARY KEY,
            favorite_focal_lengths jsonb NOT NULL DEFAULT '[]'::jsonb,
            style_keywords         text[] NOT NULL DEFAULT '{}'::text[],
            rejected_photo_ids     uuid[] NOT NULL DEFAULT '{}'::uuid[],
            piaa_lora_path         text,
            piaa_sample_count      int  NOT NULL DEFAULT 0,
            updated_at             timestamptz NOT NULL DEFAULT now()
        );
        """
    )

    # ---- agent_runs(审计/计费) -------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_runs (
            id           uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
            trail_id     uuid NOT NULL REFERENCES trails(id) ON DELETE CASCADE,
            user_id      uuid NOT NULL,
            status       text NOT NULL CHECK (status IN ('running','paused','finished','failed')),
            events       jsonb NOT NULL DEFAULT '[]'::jsonb,
            cost_usd     numeric(10,4) NOT NULL DEFAULT 0,
            tokens_in    int NOT NULL DEFAULT 0,
            tokens_out   int NOT NULL DEFAULT 0,
            started_at   timestamptz NOT NULL DEFAULT now(),
            finished_at  timestamptz
        );
        CREATE INDEX IF NOT EXISTS idx_runs_user ON agent_runs(user_id, started_at DESC);
        CREATE INDEX IF NOT EXISTS idx_runs_trail ON agent_runs(trail_id, started_at DESC);
        """
    )


def downgrade() -> None:
    for tbl in ("agent_runs", "photos", "user_preferences", "trails", "subscriptions"):
        op.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE;")
