"""make_rule_code_unique_per_rule_set

Revision ID: c8d9e0f1a2b3
Revises: c2d3e4f5a6b7
Create Date: 2026-11-25 09:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8d9e0f1a2b3'
down_revision: Union[str, Sequence[str], None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Gỡ bỏ unique toàn cục trên rule_code, chuyển thành unique kết hợp (rule_set_id, rule_code)."""
    op.drop_index('ix_tax_rules_rule_code', table_name='tax_rules')
    op.create_index(op.f('ix_tax_rules_rule_code'), 'tax_rules', ['rule_code'], unique=False)
    op.create_unique_constraint('uq_tax_rules_rule_set_rule_code', 'tax_rules', ['rule_set_id', 'rule_code'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_tax_rules_rule_set_rule_code', 'tax_rules', type_='unique')
    op.drop_index(op.f('ix_tax_rules_rule_code'), table_name='tax_rules')
    op.create_index('ix_tax_rules_rule_code', 'tax_rules', ['rule_code'], unique=True)
