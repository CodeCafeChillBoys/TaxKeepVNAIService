"""seed_prompt_medical_statement_ocr

Revision ID: b7e4a8c1f9d2
Revises: 13fe4b544704
Create Date: 2026-11-21 17:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import table, column

import os
import sys

# Đảm bảo import được module app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.prompts.expense_ocr.medical_statement_prompt import MEDICAL_STATEMENT_ONLY_SYSTEM_PROMPT

# revision identifiers, used by Alembic.
revision: str = 'b7e4a8c1f9d2'
down_revision: Union[str, Sequence[str], None] = '13fe4b544704'
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
    result = conn.execute(
        sa.text("SELECT COUNT(*) FROM ai_prompt_templates WHERE prompt_key = 'PROMPT_MEDICAL_STATEMENT_OCR'")
    ).scalar()

    if result == 0:
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


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM ai_prompt_templates WHERE prompt_key = 'PROMPT_MEDICAL_STATEMENT_OCR'")
    )
