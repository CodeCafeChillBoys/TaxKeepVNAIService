"""create_ai_prompt_templates_table

Revision ID: e63753368743
Revises: a1b2c3d4e5f6
Create Date: 2026-11-02 16:46:10.172647

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e63753368743'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'ai_prompt_templates',
        sa.Column('prompt_key', sa.String(length=100), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('variables', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('prompt_key')
    )
    op.create_index(op.f('ix_ai_prompt_templates_prompt_key'), 'ai_prompt_templates', ['prompt_key'], unique=False)
    op.create_index(op.f('ix_ai_prompt_templates_is_active'), 'ai_prompt_templates', ['is_active'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_ai_prompt_templates_is_active'), table_name='ai_prompt_templates')
    op.drop_index(op.f('ix_ai_prompt_templates_prompt_key'), table_name='ai_prompt_templates')
    op.drop_table('ai_prompt_templates')