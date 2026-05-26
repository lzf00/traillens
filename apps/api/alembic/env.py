"""Alembic environment。

设计:
- DB URL 从 env var DATABASE_URL 读,与 docker-compose.yml 一致。
- 没接 ORM models(裸 SQL migration),migration 文件自己写 op.execute()。
- Sprint 5 末接 SQLAlchemy models 后,这里换成 target_metadata = Base.metadata。
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config
db_url = os.environ.get("DATABASE_URL") or "postgresql://traillens:traillens_dev@localhost:5432/traillens"
config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None  # 裸 SQL,无 ORM


def run_migrations_offline() -> None:
    context.configure(url=db_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
