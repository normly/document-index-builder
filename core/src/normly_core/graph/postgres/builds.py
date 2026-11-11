# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
"""Private build identity, isolated from public exchange and consumer state."""

import sqlalchemy as sa
from sqlalchemy.orm import Session

from normly_core.graph.postgres.orm import (
    KnowledgeBuildORM,
    KnowledgeBaseImportORM,
    DocumentORM,
)


class PostgresBuildRepository:
    def __init__(self, session: Session):
        self.session = session

    def claim(self, build_id: str, fingerprint: str) -> None:
        self.session.execute(sa.text("SELECT pg_advisory_xact_lock(8234702)"))
        if self.session.get(KnowledgeBaseImportORM, 1) is not None:
            raise ValueError("consumer database cannot be used for a build")
        existing = self.session.get(KnowledgeBuildORM, 1)
        if existing is not None:
            if existing.build_id != build_id or existing.fingerprint != fingerprint:
                raise ValueError("database belongs to another build or configuration")
        else:
            if self.session.scalar(sa.select(sa.func.count()).select_from(DocumentORM)):
                raise ValueError("nonempty database has no build identity")
            self.session.add(
                KnowledgeBuildORM(id=1, build_id=build_id, fingerprint=fingerprint)
            )
            self.session.flush()
