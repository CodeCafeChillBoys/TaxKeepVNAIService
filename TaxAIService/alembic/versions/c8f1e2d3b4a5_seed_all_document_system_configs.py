"""seed_all_document_system_configs

Revision ID: c8f1e2d3b4a5
Revises: b7e4a8c1f9d2
Create Date: 2026-11-21 19:00:00.000000

"""
from typing import Sequence, Union
from datetime import datetime
import os
import sys

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

# Đảm bảo import được module app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.scripts.seed_system_configs import SEED_SYSTEM_CONFIGS

# revision identifiers, used by Alembic.
revision: str = 'c8f1e2d3b4a5'
down_revision: Union[str, Sequence[str], None] = 'b7e4a8c1f9d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    system_configs_table = table(
        'system_configs',
        column('config_key', sa.String),
        column('config_value', sa.String),
        column('data_type', sa.String),
        column('description', sa.String),
        column('is_active', sa.Boolean),
        column('is_deleted', sa.Boolean),
        column('created_at', sa.DateTime),
        column('updated_at', sa.DateTime),
    )

    conn = op.get_bind()
    now = datetime.utcnow()

    for item in SEED_SYSTEM_CONFIGS:
        key = item["config_key"]
        result = conn.execute(
            sa.text("SELECT COUNT(*) FROM system_configs WHERE config_key = :k"),
            {"k": key}
        ).scalar()

        if result == 0:
            op.bulk_insert(
                system_configs_table,
                [
                    {
                        'config_key': key,
                        'config_value': item["config_value"],
                        'data_type': item.get("data_type", "STRING"),
                        'description': item.get("description"),
                        'is_active': item.get("is_active", True),
                        'is_deleted': False,
                        'created_at': now,
                        'updated_at': now,
                    }
                ]
            )
        else:
            conn.execute(
                sa.text("""
                    UPDATE system_configs
                    SET config_value = :val,
                        data_type = :dt,
                        description = COALESCE(description, :desc),
                        is_active = TRUE,
                        is_deleted = FALSE,
                        updated_at = :now
                    WHERE config_key = :k
                """),
                {
                    "k": key,
                    "val": item["config_value"],
                    "dt": item.get("data_type", "STRING"),
                    "desc": item.get("description"),
                    "now": now,
                }
            )


def downgrade() -> None:
    conn = op.get_bind()
    keys_to_delete = [item["config_key"] for item in SEED_SYSTEM_CONFIGS]
    if keys_to_delete:
        conn.execute(
            sa.text("DELETE FROM system_configs WHERE config_key = ANY(:keys)"),
            {"keys": keys_to_delete}
        )
