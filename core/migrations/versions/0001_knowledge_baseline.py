# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
"""Knowledge-only baseline derived from source schema at 41a3ce2.

Only for empty standalone databases; never stamp the shared web_app database.
"""
from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy.vector
from sqlalchemy.dialects import postgresql

revision = "0001_knowledge_baseline"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table('knowledge_base_import',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('dump_version', sa.String(), nullable=False),
    sa.Column('exchange_schema_version', sa.Integer(), nullable=False),
    sa.Column('embedding_model_revision', sa.String(), nullable=False),
    sa.Column('imported_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('id = 1', name='ck_knowledge_base_import_single_row'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('rate_limit_bucket',
    sa.Column('key', sa.String(), nullable=False),
    sa.Column('window_start', sa.DateTime(timezone=True), nullable=False),
    sa.Column('request_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.PrimaryKeyConstraint('key', 'window_start')
    )
    op.create_index('ix_rate_limit_bucket_window_start', 'rate_limit_bucket', ['window_start'], unique=False)
    op.create_table('source',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('publisher', sa.String(), nullable=False),
    sa.Column('retrieval_path', sa.String(), nullable=False),
    sa.Column('legal_basis_category', sa.Enum('A', 'B', 'C', 'D', name='legal_basis_category', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('jurisdiction', sa.String(), nullable=False),
    sa.Column('reviewed_at', sa.Date(), nullable=False),
    sa.Column('responsible_person', sa.String(), nullable=False),
    sa.Column('commercial_catalog', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('contract_reference', sa.String(), nullable=True),
    sa.Column('tdm_opt_out_checked_at', sa.Date(), nullable=True),
    sa.Column('tdm_opt_out_result', sa.Enum('none_found', 'opt_out_present', name='tdm_opt_out_result', native_enum=False, create_constraint=True), nullable=True),
    sa.CheckConstraint("NOT (legal_basis_category = 'D' AND commercial_catalog)", name='ck_source_no_category_d_commercial_catalog'),
    sa.CheckConstraint("legal_basis_category != 'C' OR contract_reference IS NOT NULL", name='ck_source_category_c_requires_contract'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('work',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('retired_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.Enum('active', 'merged', name='work_status', native_enum=False, create_constraint=True), server_default='active', nullable=False),
    sa.Column('merged_into_work_id', sa.UUID(), nullable=True),
    sa.Column('created_via', sa.Enum('auto_matched', 'manual', name='work_created_via', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['merged_into_work_id'], ['work.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('delivery',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('source_id', sa.UUID(), nullable=False),
    sa.Column('content_hash', sa.String(), nullable=False),
    sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('withdrawn_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['source_id'], ['source.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source_id', 'content_hash', name='uq_delivery_source_hash')
    )
    op.create_table('document',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('retired_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('origin_issuer', sa.String(), nullable=False),
    sa.Column('origin_number', sa.String(), nullable=False),
    sa.Column('edition', sa.String(), nullable=False),
    sa.Column('part', sa.String(), nullable=True),
    sa.Column('work_id', sa.UUID(), nullable=False),
    sa.Column('created_via_delivery_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_via_delivery_id'], ['delivery.id'], ),
    sa.ForeignKeyConstraint(['work_id'], ['work.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('document_designation',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('document_id', sa.UUID(), nullable=False),
    sa.Column('issuer', sa.String(), nullable=False),
    sa.Column('designation', sa.String(), nullable=False),
    sa.Column('language', sa.String(), nullable=False),
    sa.Column('edition', sa.String(), nullable=True),
    sa.Column('is_primary', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('delivery_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['delivery_id'], ['delivery.id'], ),
    sa.ForeignKeyConstraint(['document_id'], ['document.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('issuer', 'designation', 'edition', name='uq_designation_issuer_designation_edition', postgresql_nulls_not_distinct=True)
    )
    op.create_table('document_embedding',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('document_id', sa.UUID(), nullable=False),
    sa.Column('model_name', sa.String(), nullable=False),
    sa.Column('vector', pgvector.sqlalchemy.vector.VECTOR(dim=1024), nullable=False),
    sa.Column('delivery_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['delivery_id'], ['delivery.id'], ),
    sa.ForeignKeyConstraint(['document_id'], ['document.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('document_id', 'model_name', name='uq_document_embedding_document_model')
    )
    op.create_table('document_title',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('document_id', sa.UUID(), nullable=False),
    sa.Column('language', sa.String(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('delivery_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['delivery_id'], ['delivery.id'], ),
    sa.ForeignKeyConstraint(['document_id'], ['document.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('document_id', 'language', 'title', name='uq_title_document_language_title')
    )
    op.create_table('edge',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('retired_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('from_document_id', sa.UUID(), nullable=False),
    sa.Column('to_document_id', sa.UUID(), nullable=False),
    sa.Column('edge_type', sa.Enum('references', 'replaces', 'withdrawn_by', 'based_on_law', 'adopted_from', name='edge_type', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('jurisdiction', sa.String(), nullable=True),
    sa.Column('layer', sa.Enum('free', 'commercial', name='layer', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('delivery_id', sa.UUID(), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['delivery_id'], ['delivery.id'], ),
    sa.ForeignKeyConstraint(['from_document_id'], ['document.id'], ),
    sa.ForeignKeyConstraint(['to_document_id'], ['document.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('uq_edge_active_from_to_type_jurisdiction', 'edge', ['from_document_id', 'to_document_id', 'edge_type', sa.literal_column("coalesce(jurisdiction, '')")], unique=True, postgresql_where=sa.text('revoked_at IS NULL'))
    op.create_table('identity_resolution_case',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('delivery_id', sa.UUID(), nullable=False),
    sa.Column('case_type', sa.Enum('new_document', 'work_merge', name='identity_resolution_case_type', native_enum=False, create_constraint=True), server_default='new_document', nullable=False),
    sa.Column('raw_designation', sa.String(), nullable=True),
    sa.Column('raw_issuer', sa.String(), nullable=True),
    sa.Column('reason', sa.String(), nullable=False),
    sa.Column('status', sa.Enum('pending', 'resolved', 'rejected', name='identity_resolution_status', native_enum=False, create_constraint=True), server_default='pending', nullable=False),
    sa.Column('resolved_document_id', sa.UUID(), nullable=True),
    sa.Column('source_work_id', sa.UUID(), nullable=True),
    sa.Column('target_work_id', sa.UUID(), nullable=True),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('resolved_by', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['delivery_id'], ['delivery.id'], ),
    sa.ForeignKeyConstraint(['resolved_document_id'], ['document.id'], ),
    sa.ForeignKeyConstraint(['source_work_id'], ['work.id'], ),
    sa.ForeignKeyConstraint(['target_work_id'], ['work.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('rights_classification',
    sa.Column('document_id', sa.UUID(), nullable=False),
    sa.Column('jurisdiction', sa.String(), nullable=False),
    sa.Column('may_process', sa.Boolean(), nullable=False),
    sa.Column('may_index_fulltext', sa.Boolean(), nullable=False),
    sa.Column('may_cite_passages', sa.Boolean(), nullable=False),
    sa.Column('may_export_free', sa.Boolean(), nullable=False),
    sa.Column('legal_basis_reference', sa.String(), nullable=False),
    sa.Column('classified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('classified_by', sa.String(), nullable=False),
    sa.Column('delivery_id', sa.UUID(), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['delivery_id'], ['delivery.id'], ),
    sa.ForeignKeyConstraint(['document_id'], ['document.id'], ),
    sa.PrimaryKeyConstraint('document_id', 'jurisdiction')
    )
    op.create_table('segment',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('document_id', sa.UUID(), nullable=False),
    sa.Column('delivery_id', sa.UUID(), nullable=False),
    sa.Column('sequence_number', sa.Integer(), nullable=False),
    sa.Column('heading', sa.String(), nullable=True),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('language', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['delivery_id'], ['delivery.id'], ),
    sa.ForeignKeyConstraint(['document_id'], ['document.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('document_id', 'delivery_id', 'sequence_number', name='uq_segment_document_delivery_sequence')
    )
    op.create_table('embedding',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('segment_id', sa.UUID(), nullable=False),
    sa.Column('delivery_id', sa.UUID(), nullable=False),
    sa.Column('model_name', sa.String(), nullable=False),
    sa.Column('vector', pgvector.sqlalchemy.vector.VECTOR(dim=1024), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['delivery_id'], ['delivery.id'], ),
    sa.ForeignKeyConstraint(['segment_id'], ['segment.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('segment_id', 'model_name', name='uq_embedding_segment_model')
    )
    # ### end Alembic commands ###
    op.execute("CREATE INDEX ix_document_embedding_vector_hnsw ON document_embedding USING hnsw (vector vector_cosine_ops)")
    op.execute("CREATE INDEX ix_embedding_vector_hnsw ON embedding USING hnsw (vector vector_cosine_ops)")


def downgrade():
# ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('embedding')
    op.drop_table('segment')
    op.drop_table('rights_classification')
    op.drop_table('identity_resolution_case')
    op.drop_index('uq_edge_active_from_to_type_jurisdiction', table_name='edge', postgresql_where=sa.text('revoked_at IS NULL'))
    op.drop_table('edge')
    op.drop_table('document_title')
    op.drop_table('document_embedding')
    op.drop_table('document_designation')
    op.drop_table('document')
    op.drop_table('delivery')
    op.drop_table('work')
    op.drop_table('source')
    op.drop_index('ix_rate_limit_bucket_window_start', table_name='rate_limit_bucket')
    op.drop_table('rate_limit_bucket')
    op.drop_table('knowledge_base_import')
    # ### end Alembic commands ###
