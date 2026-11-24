"""add_relationship_and_alternative_group

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-11-24 20:30:00.000000

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
revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, Sequence[str], None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Thêm cột relationship cho dependent_rules
    op.add_column(
        'dependent_rules',
        sa.Column('relationship', sa.String(length=50), nullable=True)
    )
    op.create_index(
        op.f('ix_dependent_rules_relationship'),
        'dependent_rules',
        ['relationship'],
        unique=False
    )

    # 2. Thêm cột alternative_group cho dependent_rule_documents
    op.add_column(
        'dependent_rule_documents',
        sa.Column('alternative_group', sa.String(length=50), nullable=True)
    )
    op.create_index(
        op.f('ix_dependent_rule_documents_alternative_group'),
        'dependent_rule_documents',
        ['alternative_group'],
        unique=False
    )

    # 3. Thêm cấu hình ALLOWED_RELATIONSHIPS vào system_configs (nếu chưa có)
    conn = op.get_bind()
    count_config = conn.execute(
        sa.text("SELECT COUNT(*) FROM system_configs WHERE config_key = 'ALLOWED_RELATIONSHIPS'")
    ).scalar()

    if count_config == 0:
        conn.execute(
            sa.text("""
                INSERT INTO system_configs (config_key, config_value, data_type, description, is_active, is_deleted, created_at, updated_at)
                VALUES ('ALLOWED_RELATIONSHIPS', 'CHILD, SPOUSE, PARENT, OTHER_DEPENDENT', 'LIST_STRING', 'Danh mục phân loại quan hệ người phụ thuộc chuẩn hóa (Admin có thể cấu hình)', true, false, NOW(), NOW())
            """)
        )

    # 4. Cập nhật system prompt template trong ai_prompt_templates
    conn.execute(
        sa.text("""
            UPDATE ai_prompt_templates
            SET system_prompt = :prompt,
                description = 'System prompt phân tích và bóc tách quy tắc thuế từ văn bản pháp luật PDF (tách rời từng nhóm NPT, quan hệ và nhóm giấy tờ thay thế)',
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

    # 5. Xóa cache Redis nếu có
    try:
        from app.infrastructure.redis_client import get_redis_client
        redis_cli = get_redis_client()
        if redis_cli:
            redis_cli.delete("ai:prompt:PROMPT_TAX_RULE_EXTRACTION")
    except Exception:
        pass


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM system_configs WHERE config_key = 'ALLOWED_RELATIONSHIPS'")
    )
    op.drop_index(op.f('ix_dependent_rule_documents_alternative_group'), table_name='dependent_rule_documents')
    op.drop_column('dependent_rule_documents', 'alternative_group')
    op.drop_index(op.f('ix_dependent_rules_relationship'), table_name='dependent_rules')
    op.drop_column('dependent_rules', 'relationship')
