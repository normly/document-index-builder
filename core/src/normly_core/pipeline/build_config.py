# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
"""Strict, non-secret build inputs; runtime credentials are environment-only."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from normly_core.embeddings import MODEL_NAME, MODEL_REVISION, MODEL_DIMENSION
from normly_core.pipeline.sources import SOURCE_REGISTRY
from normly_core.pipeline.docling_config import DoclingPdfConfig, parse_pdf_config


@dataclass(frozen=True)
class BuildSource:
    adapter: str
    directory: Path


@dataclass(frozen=True)
class BuildConfig:
    build_id: str
    output_version: str
    sources: tuple[BuildSource, ...]
    embedding_model_name: str
    embedding_model_revision: str
    embedding_dimension: int
    strategy_name: str
    strategy_revision: str
    docling: DoclingPdfConfig = DoclingPdfConfig()


def _keys(
    value: object, expected: set[str], label: str, optional: set[str] = frozenset()
) -> dict:
    if (
        not isinstance(value, dict)
        or not expected <= set(value)
        or set(value) - expected - optional
    ):
        raise ValueError(f"invalid {label} fields")
    return value


def load_build_config(path: Path) -> BuildConfig:
    raw = _keys(
        json.loads(path.read_text()),
        {
            "build_id",
            "output_version",
            "sources",
            "embedding_model",
            "strategy",
        },
        "build configuration",
        {"docling"},
    )
    for key in ("build_id", "output_version"):
        if not isinstance(raw[key], str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", raw[key]
        ):
            raise ValueError(f"invalid {key}")
    model = _keys(
        raw["embedding_model"], {"name", "revision", "dimension"}, "embedding model"
    )
    if model != {
        "name": MODEL_NAME,
        "revision": MODEL_REVISION,
        "dimension": MODEL_DIMENSION,
    }:
        raise ValueError("unsupported embedding model, revision or dimension")
    strategy = _keys(raw["strategy"], {"name", "revision"}, "strategy")
    if strategy != {"name": "source-adapters", "revision": "1"}:
        raise ValueError("unsupported strategy")
    if not isinstance(raw["sources"], list) or not raw["sources"]:
        raise ValueError("at least one source is required")
    sources = []
    for value in raw["sources"]:
        source = _keys(value, {"adapter", "directory"}, "source")
        if source["adapter"] not in SOURCE_REGISTRY:
            raise ValueError("unregistered source adapter")
        if not isinstance(source["directory"], str):
            raise ValueError("source directory must be a path")
        directory = Path(source["directory"])
        if not directory.is_absolute():
            directory = path.parent / directory
        directory = directory.resolve()
        if not directory.is_dir():
            raise ValueError("source directory is unreadable or absent")
        sources.append(BuildSource(source["adapter"], directory))
    if len(set(sources)) != len(sources):
        raise ValueError("duplicate source configuration")
    return BuildConfig(
        raw["build_id"],
        raw["output_version"],
        tuple(sources),
        MODEL_NAME,
        MODEL_REVISION,
        MODEL_DIMENSION,
        "source-adapters",
        "1",
        parse_pdf_config(raw.get("docling", {})),
    )
