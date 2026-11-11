# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
from datetime import datetime, timezone

from normly_core.graph.domain import ImportRecord
from normly_core.graph.postgres.exchange import PostgresKnowledgeExchangeRepository
from normly_core.exchange.tables import KNOWLEDGE_TABLES


def test_readiness_requires_a_compatible_imported_release(client, db_session, monkeypatch):
    assert client.get("/health/ready").status_code == 503
    revision = "3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3"
    monkeypatch.setenv("NORMLY_EMBEDDING_MODEL_REVISION", revision)
    PostgresKnowledgeExchangeRepository(db_session).replace_knowledge_base(
        {name: lambda: iter([]) for name in KNOWLEDGE_TABLES},
        record=ImportRecord("2026.11.1", 1, revision, datetime.now(timezone.utc)),
    )
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["knowledge_version"] == "2026.11.1"
    monkeypatch.setenv("NORMLY_EMBEDDING_MODEL_REVISION", "different")
    assert client.get("/health/ready").status_code == 503
