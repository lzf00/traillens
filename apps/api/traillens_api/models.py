"""SQLAlchemy ORM models — 与 alembic 0001 schema 严格对应。

设计原则
--------
**Migration 是单一事实来源,不是 models。**
新加 column:
  1. 先写 migration(alembic revision --autogenerate 是危险的因为我们用裸 SQL)
  2. 再加 model field
  3. 跑 contract test 验证两边对齐

为什么不让 SQLAlchemy 自动管 schema:
- pgvector / PostGIS 的列类型 ORM 不原生支持(需要 sqlalchemy-pgvector / GeoAlchemy2 额外包)
- 项目宁愿写 raw SQL 一次,不愿调 ORM 的 quirks 半天
- ORM 在这里只服务"读取的类型化",不服务"DDL 生成"
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

try:
    from sqlalchemy import (
        Column, String, Text, Integer, Numeric, DateTime, ForeignKey, CheckConstraint,
    )
    from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False


if HAS_SQLALCHEMY:
    class Base(DeclarativeBase):
        pass

    class Subscription(Base):
        __tablename__ = "subscriptions"

        user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
        stripe_customer_id: Mapped[Optional[str]] = mapped_column(Text, unique=True)
        plan: Mapped[str] = mapped_column(Text, default="free")
        quota_monthly: Mapped[int] = mapped_column(Integer, default=50)
        current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
        updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


    class Trail(Base):
        __tablename__ = "trails"

        id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
        user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
        name: Mapped[str] = mapped_column(Text, nullable=False)
        location_name: Mapped[Optional[str]] = mapped_column(Text)
        gpx_uri: Mapped[Optional[str]] = mapped_column(Text)
        # gps_bbox 是 PostGIS geometry,ORM 不映射,留给原生 SQL 处理
        state: Mapped[dict] = mapped_column(JSONB, default=dict)
        travelogue_md: Mapped[Optional[str]] = mapped_column(Text)
        next_trip_plan: Mapped[Optional[dict]] = mapped_column(JSONB)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
        updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

        photos: Mapped[list["Photo"]] = relationship(back_populates="trail", cascade="all, delete-orphan")


    class Photo(Base):
        __tablename__ = "photos"

        id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
        trail_id: Mapped[str] = mapped_column(
            UUID(as_uuid=False),
            ForeignKey("trails.id", ondelete="CASCADE"),
            nullable=False, index=True,
        )
        uri: Mapped[str] = mapped_column(Text, nullable=False)
        exif: Mapped[Optional[dict]] = mapped_column(JSONB)
        verdict: Mapped[Optional[str]] = mapped_column(Text)
        reject_reason: Mapped[Optional[str]] = mapped_column(Text)
        aesthetic: Mapped[Optional[dict]] = mapped_column(JSONB)
        critique: Mapped[Optional[str]] = mapped_column(Text)
        # embedding 是 vector(768),ORM 不映射,用 raw SQL + pgvector
        decision_trace: Mapped[list] = mapped_column(JSONB, default=list)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

        trail: Mapped[Trail] = relationship(back_populates="photos")


    class UserPreference(Base):
        __tablename__ = "user_preferences"

        user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
        favorite_focal_lengths: Mapped[list] = mapped_column(JSONB, default=list)
        style_keywords: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
        rejected_photo_ids: Mapped[list[str]] = mapped_column(ARRAY(UUID(as_uuid=False)), default=list)
        piaa_lora_path: Mapped[Optional[str]] = mapped_column(Text)
        piaa_sample_count: Mapped[int] = mapped_column(Integer, default=0)
        updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


    class AgentRun(Base):
        __tablename__ = "agent_runs"
        __table_args__ = (
            CheckConstraint("status IN ('running','paused','finished','failed')"),
        )

        id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
        trail_id: Mapped[str] = mapped_column(
            UUID(as_uuid=False),
            ForeignKey("trails.id", ondelete="CASCADE"),
            nullable=False,
        )
        user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
        status: Mapped[str] = mapped_column(Text, nullable=False)
        events: Mapped[list] = mapped_column(JSONB, default=list)
        cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), default=0)
        tokens_in: Mapped[int] = mapped_column(Integer, default=0)
        tokens_out: Mapped[int] = mapped_column(Integer, default=0)
        started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
        finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
