# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
import pytest
import sqlalchemy as sa

from normly_core.exchange.tables import KNOWLEDGE_TABLES
from normly_core.graph.domain import ImportRecord
from normly_core.graph.postgres.exchange import PostgresKnowledgeExchangeRepository
from normly_core.graph.postgres.repositories import PostgresSegmentRepository

from .helpers import NOW, make_source, make_delivery, make_document


def test_interrupted_replacement_rolls_back_content_and_import_marker(db_session):
    delivery = make_delivery(db_session, make_source(db_session), "atomic")
    document = make_document(db_session, delivery, "ATOMIC")
    segment, _ = PostgresSegmentRepository(db_session).add_segment(
        document_id=document.id, delivery_id=delivery.id, sequence_number=1,
        heading="1", text="Synthetic content", language="de",
    )
    repository = PostgresKnowledgeExchangeRepository(db_session)
    before = db_session.execute(sa.text("SELECT id, text FROM segment")).all()
    with pytest.raises(RuntimeError, match="interrupted"):
        with db_session.begin_nested():
            repository.replace_knowledge_base(
                {name: lambda: iter([]) for name in KNOWLEDGE_TABLES},
                record=ImportRecord("2026.11.1", 1, "revision", NOW),
            )
            raise RuntimeError("interrupted before commit")
    assert db_session.execute(sa.text("SELECT id, text FROM segment")).all() == before
    assert repository.imported_version() is None
    assert db_session.execute(sa.text("SELECT retired_at FROM document")).scalar_one() is None
