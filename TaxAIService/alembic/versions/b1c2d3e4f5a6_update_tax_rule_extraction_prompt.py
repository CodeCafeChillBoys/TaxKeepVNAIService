"""update_tax_rule_extraction_prompt

Revision ID: b1c2d3e4f5a6
Revises: a2b3c4d5e6f7
Create Date: 2026-11-23 22:42:00.000000

"""
from typing import Sequence, Union
import json
import os
import sys

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import table, column

# Đảm bảo import được module app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.prompts.tax_rule.tax_rule_prompts import (
    TAX_RULE_EXTRACTION_SYSTEM_PROMPT_TEMPLATE,
    TAX_RULE_EXTRACTION_PROMPT_VARIABLES,
)

# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    prompt_table = table(
        'ai_prompt_templates',
        column('prompt_key', sa.String),
        column('system_prompt', sa.Text),
        column('description', sa.String),
        column('version', sa.Integer),
        column('variables', JSONB),
        column('is_active', sa.Boolean),
        column('updated_at', sa.DateTime),
    )

    conn = op.get_bind()

    # Kiểm tra xem PROMPT_TAX_RULE_EXTRACTION đã có trong DB chưa
    count_tax_rule = conn.execute(
        sa.text("SELECT COUNT(*) FROM ai_prompt_templates WHERE prompt_key = 'PROMPT_TAX_RULE_EXTRACTION'")
    ).scalar()

    if count_tax_rule == 0:
        op.bulk_insert(
            prompt_table,
            [
                {
                    'prompt_key': 'PROMPT_TAX_RULE_EXTRACTION',
                    'system_prompt': TAX_RULE_EXTRACTION_SYSTEM_PROMPT_TEMPLATE,
                    'description': 'System prompt phân tích và bóc tách quy tắc thuế từ văn bản pháp luật PDF (tách rời từng nhóm người phụ thuộc)',
                    'version': 1,
                    'variables': TAX_RULE_EXTRACTION_PROMPT_VARIABLES,
                    'is_active': True,
                    'updated_at': sa.func.now(),
                }
            ]
        )
    else:
        conn.execute(
            sa.text("""
                UPDATE ai_prompt_templates
                SET system_prompt = :prompt,
                    description = 'System prompt phân tích và bóc tách quy tắc thuế từ văn bản pháp luật PDF (tách rời từng nhóm người phụ thuộc)',
                    variables = CAST(:vars AS jsonb),
                    version = version + 1,
                    updated_at = NOW()
                WHERE prompt_key = 'PROMPT_TAX_RULE_EXTRACTION'
            """),
            {
                "prompt": TAX_RULE_EXTRACTION_SYSTEM_PROMPT_TEMPLATE,
                "vars": json.dumps(TAX_RULE_EXTRACTION_PROMPT_VARIABLES),
            }
        )

    # Xóa cache Redis nếu có
    try:
        from app.infrastructure.redis_client import get_redis_client
        redis_cli = get_redis_client()
        if redis_cli:
            redis_cli.delete("ai:prompt:PROMPT_TAX_RULE_EXTRACTION")
    except Exception:
        pass


def downgrade() -> None:
    pass
