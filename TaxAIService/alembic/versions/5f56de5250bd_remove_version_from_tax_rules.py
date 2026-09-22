"""remove_version_from_tax_rules

Revision ID: 5f56de5250bd
Revises: cdf4a74b89e7
Create Date: 2026-09-22 12:10:59.206066

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


# revision identifiers, used by Alembic.
revision: str = '5f56de5250bd'
down_revision: Union[str, Sequence[str], None] = 'cdf4a74b89e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('tax_rules', 'version')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('tax_rules', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))

