import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# 1. Thêm thư mục gốc vào đường dẫn hệ thống để nhận diện package app
sys.path.insert(0, os.path.abspath("."))

# 2. Import cấu hình và Models để Alembic quét bảng
from app.core.config import settings
from app.infrastructure.database import Base
import app.models  # Import toàn bộ models từ app/models/__init__.py

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# 3. Đồng bộ chuỗi kết nối từ file .env vào cấu hình Alembic
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 4. Gán metadata cho tính năng tự động sinh migration (autogenerate)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
