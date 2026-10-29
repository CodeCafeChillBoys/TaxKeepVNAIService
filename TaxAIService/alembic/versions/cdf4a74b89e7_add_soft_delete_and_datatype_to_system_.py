"""add_soft_delete_and_datatype_to_system_configs

Revision ID: cdf4a74b89e7
Revises: 6c92261815cc
Create Date: 2026-09-17 10:49:37.248005

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


# revision identifiers, used by Alembic.
revision: str = 'cdf4a74b89e7'
down_revision: Union[str, Sequence[str], None] = '6c92261815cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('system_configs', sa.Column('data_type', sa.String(length=20), server_default='STRING', nullable=False))
    op.add_column('system_configs', sa.Column('description', sa.String(length=255), nullable=True))
    op.add_column('system_configs', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('system_configs', sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('system_configs', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('system_configs', sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False))

    op.create_index(op.f('ix_system_configs_is_active'), 'system_configs', ['is_active'], unique=False)
    op.create_index(op.f('ix_system_configs_is_deleted'), 'system_configs', ['is_deleted'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_system_configs_is_deleted'), table_name='system_configs')
    op.drop_index(op.f('ix_system_configs_is_active'), table_name='system_configs')
    op.drop_column('system_configs', 'created_at')
    op.drop_column('system_configs', 'deleted_at')
    op.drop_column('system_configs', 'is_deleted')
    op.drop_column('system_configs', 'is_active')
    op.drop_column('system_configs', 'description')
    op.drop_column('system_configs', 'data_type')
