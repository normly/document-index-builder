# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from normly_core.embeddings import EmbeddingModel, MODEL_REVISION
from normly_core.graph.postgres.lifecycle import PostgresLifecycleRepository
from normly_api.dependencies import get_session

from normly_api.errors import COMMON_ERROR_RESPONSES, register_exception_handlers
from normly_api.rate_limit import enforce_rate_limit
from normly_api.routers.documents import documents_router
from normly_api.routers.edges import edges_router
from normly_api.routers.export import export_router
from normly_api.routers.rights import rights_router
from normly_api.routers.segments import segments_router
from normly_api.routers.search import search_router
from normly_api.routers.validity import validity_router
from normly_api.routers.work import work_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    database_url = os.environ["NORMLY_DATABASE_URL"]
    engine = create_engine(database_url)
    app.state.engine = engine

    # Loaded once at startup, not per-request: the same real,
    # multi-hundred-MB model the ingestion pipeline and chat/ use -- reusing
    # the single already-established EmbeddingModel class, not a second one.
    app.state.embedding_model = EmbeddingModel()

    try:
        yield
    finally:
        engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="normly API",
        version="1.0.0",
        description=(
            "Deterministic reference-graph queries over normly's free content. "
            "No authentication required for free-tier jurisdictions."
        ),
        license_info={
            "name": "AGPL-3.0-or-later",
            "url": "https://www.gnu.org/licenses/agpl-3.0.html",
        },
        lifespan=lifespan,
    )

    @app.get(
        "/health/ready", tags=["health"], responses={503: COMMON_ERROR_RESPONSES[503]}
    )
    def readiness(session: Session = Depends(get_session)) -> dict[str, str]:
        record = PostgresLifecycleRepository(session).ready_record(
            os.environ.get("NORMLY_EMBEDDING_MODEL_REVISION", MODEL_REVISION)
        )
        if record is None:
            raise HTTPException(status_code=503, detail="knowledge release not ready")
        return {"status": "ready", "knowledge_version": record.dump_version}

    # Every router gets the 400/503 pair, because the handlers registered just
    # below can fire on any route regardless of what that route declares. The
    # 404s are NOT here: only some routes can raise one, and claiming the rest
    # can is worse documentation than claiming nothing.
    #
    # search_router MUST be included before documents_router. Starlette tries
    # routes in registration order across the whole app; documents_router
    # registers GET /v1/documents/{document_id} with document_id: uuid.UUID,
    # and "search" is a syntactically valid path segment for that route. If
    # documents_router were registered first, a request to
    # /v1/documents/search would match {document_id} first and fail UUID
    # coercion with a 400 -- Starlette does not fall through to try
    # search_router's /v1/documents/search afterwards.
    app.include_router(
        search_router,
        responses=COMMON_ERROR_RESPONSES,
        dependencies=[Depends(enforce_rate_limit)],
    )
    app.include_router(
        documents_router,
        responses=COMMON_ERROR_RESPONSES,
        dependencies=[Depends(enforce_rate_limit)],
    )
    app.include_router(
        edges_router,
        responses=COMMON_ERROR_RESPONSES,
        dependencies=[Depends(enforce_rate_limit)],
    )
    app.include_router(
        work_router,
        responses=COMMON_ERROR_RESPONSES,
        dependencies=[Depends(enforce_rate_limit)],
    )
    app.include_router(
        rights_router,
        responses=COMMON_ERROR_RESPONSES,
        dependencies=[Depends(enforce_rate_limit)],
    )
    app.include_router(
        segments_router,
        responses=COMMON_ERROR_RESPONSES,
        dependencies=[Depends(enforce_rate_limit)],
    )
    app.include_router(
        export_router,
        responses=COMMON_ERROR_RESPONSES,
        dependencies=[Depends(enforce_rate_limit)],
    )
    app.include_router(
        validity_router,
        responses=COMMON_ERROR_RESPONSES,
        dependencies=[Depends(enforce_rate_limit)],
    )
    register_exception_handlers(app)
    return app


app = create_app()
