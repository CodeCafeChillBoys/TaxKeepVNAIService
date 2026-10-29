"""add_admin_id_to_tax_rule_sets

Revision ID: e3f281b9d4a1
Revises: bec9171d3258
Create Date: 2026-09-12 07:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3f281b9d4a1'
down_revision: Union[str, Sequence[str], None] = 'bec9171d3258'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('tax_rule_sets', sa.Column('admin_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_tax_rule_sets_admin_id'), 'tax_rule_sets', ['admin_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_tax_rule_sets_admin_id'), table_name='tax_rule_sets')
    op.drop_column('tax_rule_sets', 'admin_id')
