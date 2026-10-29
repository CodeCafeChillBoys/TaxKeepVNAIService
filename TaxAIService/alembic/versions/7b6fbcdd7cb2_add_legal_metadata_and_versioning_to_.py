"""add_legal_metadata_and_versioning_to_documents_and_chunks

Revision ID: 7b6fbcdd7cb2
Revises: 061b32a9e2b2
Create Date: 2026-09-10 16:40:38.422552

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7b6fbcdd7cb2'
down_revision: Union[str, Sequence[str], None] = '061b32a9e2b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Đảm bảo extension pgvector được kích hoạt
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Bổ sung các cột metadata cho document_chunks
    op.add_column('document_chunks', sa.Column('page_number', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('document_chunks', sa.Column('article', sa.String(length=100), nullable=True))
    op.add_column('document_chunks', sa.Column('clause', sa.String(length=100), nullable=True))
    op.add_column('document_chunks', sa.Column('point', sa.String(length=100), nullable=True))
    op.add_column('document_chunks', sa.Column('status', sa.String(length=50), nullable=False, server_default='Active'))
    op.add_column('document_chunks', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
    op.alter_column('document_chunks', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.create_index(op.f('ix_document_chunks_status'), 'document_chunks', ['status'], unique=False)

    # 3. Bổ sung các cột versioning & metadata cho documents
    op.add_column('documents', sa.Column('document_code', sa.String(length=100), nullable=False, server_default='DOC-DEFAULT'))
    op.add_column('documents', sa.Column('total_pages', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('documents', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('documents', sa.Column('status', sa.String(length=50), nullable=False, server_default='Draft'))
    op.add_column('documents', sa.Column('effective_from', sa.String(length=50), nullable=True))
    op.add_column('documents', sa.Column('effective_to', sa.String(length=50), nullable=True))
    op.add_column('documents', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.alter_column('documents', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.create_index(op.f('ix_documents_document_code'), 'documents', ['document_code'], unique=True)
    op.create_index(op.f('ix_documents_status'), 'documents', ['status'], unique=False)

    # 4. Xóa server_default sau khi gán cho dữ liệu cũ (nếu có) để schema sạch
    op.alter_column('document_chunks', 'page_number', server_default=None)
    op.alter_column('document_chunks', 'status', server_default=None)
    op.alter_column('document_chunks', 'version', server_default=None)
    op.alter_column('documents', 'document_code', server_default=None)
    op.alter_column('documents', 'total_pages', server_default=None)
    op.alter_column('documents', 'version', server_default=None)
    op.alter_column('documents', 'status', server_default=None)
    op.alter_column('documents', 'updated_at', server_default=None)

    # 5. Tạo Index HNSW cho cột embedding trên document_chunks
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Xóa HNSW Index
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw;")

    # 2. Drop index & columns bảng documents
    op.drop_index(op.f('ix_documents_status'), table_name='documents')
    op.drop_index(op.f('ix_documents_document_code'), table_name='documents')
    op.alter_column('documents', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.drop_column('documents', 'updated_at')
    op.drop_column('documents', 'effective_to')
    op.drop_column('documents', 'effective_from')
    op.drop_column('documents', 'status')
    op.drop_column('documents', 'version')
    op.drop_column('documents', 'total_pages')
    op.drop_column('documents', 'document_code')

    # 3. Drop index & columns bảng document_chunks
    op.drop_index(op.f('ix_document_chunks_status'), table_name='document_chunks')
    op.alter_column('document_chunks', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.drop_column('document_chunks', 'version')
    op.drop_column('document_chunks', 'status')
    op.drop_column('document_chunks', 'point')
    op.drop_column('document_chunks', 'clause')
    op.drop_column('document_chunks', 'article')
    op.drop_column('document_chunks', 'page_number')
