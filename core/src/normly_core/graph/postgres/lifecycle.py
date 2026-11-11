# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
"""Consumer lifecycle coordination, never a user-data or ingestion concern."""

import sqlalchemy as sa
from sqlalchemy.orm import Session

from normly_core.embeddings import MODEL_REVISION
from normly_core.exchange.manifest import EXCHANGE_SCHEMA_VERSION
from normly_core.graph.postgres.exchange import PostgresKnowledgeExchangeRepository
from normly_core.graph.postgres.orm import KnowledgeBuildORM

SCHEMA_REVISION = "0002_build_identity"


class PostgresLifecycleRepository:
    def __init__(self, session: Session):
        self.session = session
        self.exchange = PostgresKnowledgeExchangeRepository(session)

    def lock_and_current(self):
        self.session.execute(sa.text("SELECT pg_advisory_xact_lock(8234703)"))
        if self.session.get(KnowledgeBuildORM, 1) is not None:
            raise ValueError("cannot import a public release into a build database")
        return self.exchange.imported_version()

    def ready_record(self, expected_model_revision: str):
        record = self.exchange.imported_version()
        revision = self.session.execute(
            sa.text("SELECT version_num FROM alembic_version")
        ).scalar_one_or_none()
        if (
            revision != SCHEMA_REVISION
            or record is None
            or record.exchange_schema_version != EXCHANGE_SCHEMA_VERSION
            or record.embedding_model_revision != expected_model_revision
            or expected_model_revision != MODEL_REVISION
        ):
            return None
        return record
