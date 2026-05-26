-- 容器首次启动时自动执行。
-- 启用 TrailLens 依赖的 Postgres 扩展。
-- (DDL 由 apps/api 的 Alembic migration 维护,这里只加扩展。)

CREATE EXTENSION IF NOT EXISTS vector;     -- pgvector,§4.2 photos.embedding
CREATE EXTENSION IF NOT EXISTS postgis;    -- §4.2 trails.gps_bbox
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Langfuse 共用同一个 Postgres 实例,但用单独 DB,避免与业务库混在一起
CREATE DATABASE traillens_langfuse;
