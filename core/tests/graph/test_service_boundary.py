# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors

import importlib.util
from pathlib import Path

import sqlalchemy as sa


def test_migration_creates_only_knowledge_and_local_operational_tables(db_url):
    from normly_core.migrate import upgrade_to_head

    upgrade_to_head(db_url, Path(__file__).parents[2])
    engine = sa.create_engine(db_url)
    try:
        inspector = sa.inspect(engine)
        tables = set(inspector.get_table_names())
        assert tables == {
            "source", "delivery", "work", "document", "document_designation",
            "document_title", "rights_classification", "edge", "segment",
            "embedding", "document_embedding", "identity_resolution_case",
            "knowledge_base_import", "rate_limit_bucket", "alembic_version",
        }
        for table in tables:
            assert all(fk["referred_table"] in tables for fk in inspector.get_foreign_keys(table))
        assert {i["name"] for i in inspector.get_indexes("embedding")} >= {"ix_embedding_vector_hnsw"}
        assert {i["name"] for i in inspector.get_indexes("document_embedding")} >= {"ix_document_embedding_vector_hnsw"}
        upgrade_to_head(db_url, Path(__file__).parents[2])
        assert set(sa.inspect(engine).get_table_names()) == tables
    finally:
        engine.dispose()


def test_repositories_do_not_expose_user_state():
    from normly_core.graph.postgres import repositories

    assert hasattr(repositories, "PostgresDocumentRepository")
    assert not hasattr(repositories, "PostgresAccountRepository")
    assert not hasattr(repositories, "PostgresChatRepository")


def test_baseline_preserves_legacy_sql_types_and_server_defaults(migrated_engine):
    inspector = sa.inspect(migrated_engine)
    expected_defaults = {
        ("source", "commercial_catalog"): "false",
        ("document_designation", "is_primary"): "false",
        ("work", "status"): "'active'::character varying",
        ("identity_resolution_case", "case_type"): "'new_document'::character varying",
        ("identity_resolution_case", "status"): "'pending'::character varying",
        ("rate_limit_bucket", "request_count"): "0",
    }
    for (table, column), expected in expected_defaults.items():
        columns = {c["name"]: c for c in inspector.get_columns(table)}
        assert columns[column]["default"] == expected, (table, column)
    text_column = next(c for c in inspector.get_columns("segment") if c["name"] == "text")
    assert str(text_column["type"]) == "TEXT"
