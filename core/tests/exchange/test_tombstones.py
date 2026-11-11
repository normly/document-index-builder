# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
"""Knowledge-only tombstone regression, without the old user-schema coupling."""

import stat

import sqlalchemy as sa

from normly_core.exchange import __main__ as cli
from normly_core.exchange.tables import KNOWLEDGE_TABLES
from normly_core.exchange.tombstones import build_document, parse_document
from normly_core.graph.domain import ImportRecord
from normly_core.graph.postgres.exchange import PostgresKnowledgeExchangeRepository
from normly_core.graph.postgres.orm import Base
from normly_core.graph.postgres.repositories import (
    PostgresDocumentRepository,
    PostgresSegmentRepository,
)

from .helpers import NOW, make_source, make_delivery, make_document


def test_tombstone_support_roundtrips_identifiers_without_restoring_content(db_session):
    delivery = make_delivery(db_session, make_source(db_session), "tombstone")
    document = make_document(db_session, delivery, "RETIRED")
    PostgresSegmentRepository(db_session).add_segment(
        document_id=document.id,
        delivery_id=delivery.id,
        sequence_number=1,
        heading="Synthetic",
        text="Synthetic text to purge",
        language="de",
    )
    repository = PostgresKnowledgeExchangeRepository(db_session)
    repository.replace_knowledge_base(
        {name: lambda: iter([]) for name in KNOWLEDGE_TABLES},
        record=ImportRecord("2026.11.1", 1, "revision", NOW),
    )
    support = repository.export_tombstone_support()
    assert {r["id"] for r in support["document"]} == {str(document.id)}
    encoded = build_document(support, created_at=NOW)
    assert "Synthetic text to purge" not in encoded
    rows, _ = parse_document(encoded)
    for name in reversed(KNOWLEDGE_TABLES):
        db_session.execute(sa.delete(Base.metadata.tables[name]))
    repository.restore_tombstone_support(rows, restored_at=NOW)
    repository.restore_tombstone_support(rows, restored_at=NOW)
    assert (
        db_session.scalar(
            sa.select(sa.func.count()).select_from(Base.metadata.tables["document"])
        )
        == 1
    )
    assert (
        db_session.scalar(
            sa.select(sa.func.count()).select_from(Base.metadata.tables["segment"])
        )
        == 0
    )
    assert (
        PostgresDocumentRepository(db_session).get_document_for_jurisdiction(
            document.id, "DE"
        )
        is None
    )


def test_keygen_needs_no_database_and_never_overwrites_keys(tmp_path, monkeypatch):
    monkeypatch.delenv("NORMLY_DATABASE_URL", raising=False)
    private, public = tmp_path / "private.pem", tmp_path / "public.pem"
    command = ["keygen", "--private", str(private), "--public", str(public)]
    assert cli.main(command) == 0
    original = private.read_bytes()
    assert stat.S_IMODE(private.stat().st_mode) == 0o600
    assert stat.S_IMODE(public.stat().st_mode) == 0o644
    assert cli.main(command) == 1
    assert private.read_bytes() == original
