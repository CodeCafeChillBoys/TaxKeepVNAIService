"""make_medical_prompts_dynamic

Revision ID: d9a2e3f4b5c6
Revises: c8f1e2d3b4a5
Create Date: 2026-11-21 19:10:00.000000

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

from app.prompts.expense_ocr.medical_statement_prompt import (
    MEDICAL_STATEMENT_RULES,
    MEDICAL_STATEMENT_ONLY_SYSTEM_PROMPT,
)
from app.prompts.expense_ocr.expense_ocr_prompt import EXPENSE_OCR_SYSTEM_PROMPT_TEMPLATE

# revision identifiers, used by Alembic.
revision: str = 'd9a2e3f4b5c6'
down_revision: Union[str, Sequence[str], None] = 'c8f1e2d3b4a5'
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
    )

    conn = op.get_bind()

    # 1. Thêm hoặc cập nhật PROMPT_MEDICAL_STATEMENT_RULES
    count_rules = conn.execute(
        sa.text("SELECT COUNT(*) FROM ai_prompt_templates WHERE prompt_key = 'PROMPT_MEDICAL_STATEMENT_RULES'")
    ).scalar()

    if count_rules == 0:
        op.bulk_insert(
            prompt_table,
            [
                {
                    'prompt_key': 'PROMPT_MEDICAL_STATEMENT_RULES',
                    'system_prompt': MEDICAL_STATEMENT_RULES,
                    'description': 'Quy tắc bóc tách bảng kê chi phí KCB (Mục 7a) chèn động vào hóa đơn chi phí',
                    'version': 1,
                    'variables': [],
                    'is_active': True,
                }
            ]
        )
    else:
        conn.execute(
            sa.text("""
                UPDATE ai_prompt_templates
                SET system_prompt = :prompt,
                    description = 'Quy tắc bóc tách bảng kê chi phí KCB (Mục 7a) chèn động vào hóa đơn chi phí',
                    version = version + 1
                WHERE prompt_key = 'PROMPT_MEDICAL_STATEMENT_RULES'
            """),
            {"prompt": MEDICAL_STATEMENT_RULES}
        )

    # 2. Cập nhật PROMPT_EXPENSE_OCR dùng template động có placeholder {medical_statement_rules}
    conn.execute(
        sa.text("""
            UPDATE ai_prompt_templates
            SET system_prompt = :prompt,
                variables = CAST(:vars AS jsonb),
                version = version + 1
            WHERE prompt_key = 'PROMPT_EXPENSE_OCR'
        """),
        {
            "prompt": EXPENSE_OCR_SYSTEM_PROMPT_TEMPLATE,
            "vars": json.dumps(["categories_text", "medical_statement_rules"]),
        }
    )

    # 3. Cập nhật PROMPT_MEDICAL_STATEMENT_OCR bản mới nhất (chỉ gồm ELIGIBLE / EXCLUDED)
    count_statement = conn.execute(
        sa.text("SELECT COUNT(*) FROM ai_prompt_templates WHERE prompt_key = 'PROMPT_MEDICAL_STATEMENT_OCR'")
    ).scalar()

    if count_statement == 0:
        op.bulk_insert(
            prompt_table,
            [
                {
                    'prompt_key': 'PROMPT_MEDICAL_STATEMENT_OCR',
                    'system_prompt': MEDICAL_STATEMENT_ONLY_SYSTEM_PROMPT,
                    'description': 'System prompt chuyên biệt bóc tách Bảng kê chi phí khám bệnh, chữa bệnh (Mẫu số 01/BV, 02/BV)',
                    'version': 1,
                    'variables': ['medical_doc_type_code', 'medical_categories_guide'],
                    'is_active': True,
                }
            ]
        )
    else:
        conn.execute(
            sa.text("""
                UPDATE ai_prompt_templates
                SET system_prompt = :prompt,
                    variables = CAST(:vars AS jsonb),
                    version = version + 1
                WHERE prompt_key = 'PROMPT_MEDICAL_STATEMENT_OCR'
            """),
            {
                "prompt": MEDICAL_STATEMENT_ONLY_SYSTEM_PROMPT,
                "vars": json.dumps(["medical_doc_type_code", "medical_categories_guide"]),
            }
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM ai_prompt_templates WHERE prompt_key = 'PROMPT_MEDICAL_STATEMENT_RULES'")
    )
