# syntax=docker/dockerfile:1.7
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
ARG PYTHON_IMAGE=python:3.12-slim@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.12.23@sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21
ARG E5_REVISION=3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3
FROM ${UV_IMAGE} AS uv
FROM ${PYTHON_IMAGE} AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv UV_PYTHON=/usr/local/bin/python3 \
    UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy PATH=/app/.venv/bin:$PATH
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 normly \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin normly
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY core/pyproject.toml core/
COPY api/pyproject.toml api/

FROM base AS retrieval-deps
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --group build --all-packages \
    --extra retrieval --extra exchange --no-install-workspace

FROM base AS builder-deps
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 fonts-liberation \
    && rm -rf /var/lib/apt/lists/*
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --group build --package normly-core \
    --extra builder --extra exchange --no-install-workspace

FROM retrieval-deps AS embedding-weights
ARG E5_REVISION
ENV HF_HUB_DISABLE_TELEMETRY=1
COPY docker/prepare-models.py core/src/normly_core/model_artifacts.py /app/
RUN --mount=type=cache,target=/tmp/hf HF_HOME=/tmp/hf python /app/prepare-models.py --kind embeddings --output /opt/models

FROM builder-deps AS docling-weights
ENV HF_HUB_DISABLE_TELEMETRY=1
COPY docker/prepare-models.py core/src/normly_core/model_artifacts.py /app/
RUN --mount=type=cache,target=/tmp/hf HF_HOME=/tmp/hf python /app/prepare-models.py --kind docling --output /opt/models

FROM retrieval-deps AS retrieval
ARG E5_REVISION
ENV HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 \
    NORMLY_EMBEDDING_MODEL_PATH=/opt/models/multilingual-e5-large \
    NORMLY_EMBEDDING_MODEL_REVISION=${E5_REVISION} NORMLY_CORE_DIR=/app/core
COPY --from=embedding-weights --chown=10001:10001 /opt/models /opt/models
COPY core /app/core
COPY api /app/api
COPY LICENSE /app/LICENSE
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --group build --all-packages --extra retrieval --extra exchange --no-build-isolation --no-editable
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "normly_api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

FROM builder-deps AS builder
ARG E5_REVISION
ARG SOURCE_COMMIT=development
ENV HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 \
    NORMLY_EMBEDDING_MODEL_PATH=/opt/models/multilingual-e5-large \
    NORMLY_EMBEDDING_MODEL_REVISION=${E5_REVISION} NORMLY_CORE_DIR=/app/core \
    NORMLY_DOCLING_ARTIFACTS_PATH=/opt/models/docling NORMLY_SOURCE_COMMIT=${SOURCE_COMMIT}
COPY --from=embedding-weights --chown=10001:10001 /opt/models /opt/models
COPY --from=docling-weights --chown=10001:10001 /opt/models/docling /opt/models/docling
COPY core /app/core
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --group build --package normly-core --extra builder --extra exchange --no-build-isolation --no-editable
COPY LICENSE /app/LICENSE
USER 10001:10001
ENTRYPOINT ["python", "-m", "normly_core.pipeline"]
CMD ["--help"]
