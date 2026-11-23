"""split_required_documents_into_table

Revision ID: a2b3c4d5e6f7
Revises: d9a2e3f4b5c6
Create Date: 2026-11-23 21:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, Sequence[str], None] = 'd9a2e3f4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tạo bảng dependent_rule_documents
    op.create_table(
        'dependent_rule_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'dependent_rule_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('dependent_rules.id', ondelete='CASCADE'),
            nullable=False
        ),
        sa.Column('doc_type', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('is_mandatory', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_dependent_rule_documents_id', 'dependent_rule_documents', ['id'])
    op.create_index('ix_dependent_rule_documents_dependent_rule_id', 'dependent_rule_documents', ['dependent_rule_id'])
    op.create_index('ix_dependent_rule_documents_doc_type', 'dependent_rule_documents', ['doc_type'])

    # 2. Chuyển dữ liệu cũ từ JSONB trong dependent_rules sang dependent_rule_documents (nếu có)
    conn = op.get_bind()
    conn.execute(sa.text("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns 
                WHERE table_name = 'dependent_rules' AND column_name = 'required_documents'
            ) THEN
                INSERT INTO dependent_rule_documents (id, dependent_rule_id, doc_type, name, is_mandatory, description, created_at, updated_at)
                SELECT 
                    gen_random_uuid(),
                    dr.id,
                    COALESCE(doc->>'docType', doc->>'doc_type', 'OTHER'),
                    COALESCE(doc->>'name', doc->>'docType', doc->>'doc_type', 'Giấy tờ'),
                    COALESCE((doc->>'isMandatory')::boolean, (doc->>'is_mandatory')::boolean, true),
                    doc->>'description',
                    NOW(),
                    NOW()
                FROM dependent_rules dr,
                     jsonb_array_elements(
                         CASE 
                             WHEN jsonb_typeof(dr.required_documents) = 'array' THEN dr.required_documents 
                             ELSE '[]'::jsonb 
                         END
                     ) AS doc
                WHERE dr.required_documents IS NOT NULL 
                  AND jsonb_array_length(
                         CASE 
                             WHEN jsonb_typeof(dr.required_documents) = 'array' THEN dr.required_documents 
                             ELSE '[]'::jsonb 
                         END
                     ) > 0;
            END IF;
        END $$;
    """))

    # 3. Xóa cột required_documents khỏi bảng dependent_rules
    op.drop_column('dependent_rules', 'required_documents')


def downgrade() -> None:
    # 1. Thêm lại cột required_documents vào bảng dependent_rules
    op.add_column(
        'dependent_rules',
        sa.Column('required_documents', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]')
    )

    # 2. Đồng bộ ngược từ dependent_rule_documents về dependent_rules (nếu cần)
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE dependent_rules dr
        SET required_documents = COALESCE(
            (
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'id', d.id,
                        'docType', d.doc_type,
                        'name', d.name,
                        'isMandatory', d.is_mandatory,
                        'description', d.description
                    )
                )
                FROM dependent_rule_documents d
                WHERE d.dependent_rule_id = dr.id
            ),
            '[]'::jsonb
        );
    """))

    # 3. Xóa bảng dependent_rule_documents
    op.drop_table('dependent_rule_documents')
