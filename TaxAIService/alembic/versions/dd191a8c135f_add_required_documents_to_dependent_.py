"""add_required_documents_to_dependent_rules

Revision ID: dd191a8c135f
Revises: 5f56de5250bd
Create Date: 2026-09-22 12:43:44.520836

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'dd191a8c135f'
down_revision: Union[str, Sequence[str], None] = '5f56de5250bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('dependent_rules', sa.Column('required_documents', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('dependent_rules', 'required_documents')

