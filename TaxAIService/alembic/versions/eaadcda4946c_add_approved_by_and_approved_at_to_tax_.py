"""add_approved_by_and_approved_at_to_tax_rule_sets

Revision ID: eaadcda4946c
Revises: e3f281b9d4a1
Create Date: 2026-09-13 00:06:23.815794

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


# revision identifiers, used by Alembic.
revision: str = 'eaadcda4946c'
down_revision: Union[str, Sequence[str], None] = 'e3f281b9d4a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('tax_rule_sets', sa.Column('approved_by', sa.UUID(), nullable=True))
    op.add_column('tax_rule_sets', sa.Column('approved_at', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_tax_rule_sets_approved_by'), 'tax_rule_sets', ['approved_by'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_tax_rule_sets_approved_by'), table_name='tax_rule_sets')
    op.drop_column('tax_rule_sets', 'approved_at')
    op.drop_column('tax_rule_sets', 'approved_by')
