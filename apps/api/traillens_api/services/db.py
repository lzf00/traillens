"""SQLAlchemy engine + session 管理。

策略:延迟初始化 — 没有 DATABASE_URL 时不连库,允许 store.py 走 in-memory fallback。
这让单测 / 离线 demo 继续工作,不强制装 postgres。
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

_engine = None
_SessionLocal = None


def _init():
    global _engine, _SessionLocal
    if _engine is not None:
        return
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        return  # 留空 → store.py 走 dict 路径

    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
    except ImportError:
        return

    # 连接池:默认 5+10 在 SSE 长连接 + 同步 DB 场景下会瞬间耗尽
    # pool_size=20 主池;max_overflow=40 峰值;recycle 30 分钟防 MySQL/PG 侧 idle 断
    _engine = create_engine(
        db_url,
        pool_pre_ping=True,
        future=True,
        pool_size=int(os.environ.get("DB_POOL_SIZE", "20")),
        max_overflow=int(os.environ.get("DB_MAX_OVERFLOW", "40")),
        pool_recycle=int(os.environ.get("DB_POOL_RECYCLE", "1800")),
        pool_timeout=int(os.environ.get("DB_POOL_TIMEOUT", "30")),
    )
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False, future=True)


def has_db() -> bool:
    _init()
    return _SessionLocal is not None


@contextmanager
def session() -> Iterator:
    _init()
    if _SessionLocal is None:
        raise RuntimeError("no DATABASE_URL configured")
    s = _SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
