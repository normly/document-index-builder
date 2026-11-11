# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
"""Build into isolated storage and emit a verified, immutable local release."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from normly_core.exchange.exporter import export_dump
from normly_core.exchange.importer import verify_dump
from normly_core.graph.postgres.builds import PostgresBuildRepository
from normly_core.graph.postgres.exchange import PostgresKnowledgeExchangeRepository
from normly_core.graph.postgres.repositories import PostgresDocumentRepository
from normly_core.migrate import upgrade_to_head
from normly_core.pipeline.build_config import BuildConfig
from normly_core.pipeline.cli import build_adapter
from normly_core.pipeline.docling_extraction import strict_extraction
from normly_core.pipeline.docling_config import use_pdf_config
from normly_core.pipeline.runner import run_adapter
from normly_core.pipeline.sources import SOURCE_REGISTRY


def input_hashes(config: BuildConfig) -> dict[str, str]:
    hashes = {}
    for index, source in enumerate(config.sources):
        for path in sorted(source.directory.rglob("*")):
            if path.is_symlink():
                raise ValueError("symlinked source inputs are not supported")
            if path.is_file():
                hashes[f"{index}/{path.relative_to(source.directory).as_posix()}"] = (
                    hashlib.sha256(path.read_bytes()).hexdigest()
                )
    return hashes


def run_build(
    config: BuildConfig, *, database_url: str, output_dir: Path, signing_key_file: Path
) -> Path:
    destination = output_dir / config.output_version
    if destination.exists():
        raise FileExistsError("output version already exists")
    output_dir.mkdir(parents=True, exist_ok=True)
    reservation = output_dir / f".{config.output_version}.lock"
    reservation.mkdir()  # Exclusive across concurrent builders of this output version.
    engine = None
    try:
        private_pem = signing_key_file.read_bytes()
        key = serialization.load_pem_private_key(private_pem, password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError("an Ed25519 release key is required")
        public_pem = key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        hashes = input_hashes(config)
        fingerprint = hashlib.sha256(
            json.dumps(
                {"config": asdict(config), "inputs": hashes},
                default=str,
                sort_keys=True,
            ).encode()
        ).hexdigest()
        core_dir = Path(os.environ.get("NORMLY_CORE_DIR", Path(__file__).parents[3]))
        upgrade_to_head(database_url, core_dir)
        engine = create_engine(database_url)
        with tempfile.TemporaryDirectory(prefix=".build-", dir=output_dir) as scratch:
            with Session(engine) as session, session.begin():
                PostgresBuildRepository(session).claim(config.build_id, fingerprint)
                with strict_extraction(), use_pdf_config(config.docling):
                    for source in config.sources:
                        adapter = build_adapter(
                            source.adapter, directory=source.directory, session=session
                        )
                        summary = run_adapter(adapter, session)
                        if (
                            summary.records_failed
                            or summary.records_enqueued_for_review
                        ):
                            raise ValueError(
                                "partial or failed ingestion cannot produce a release"
                            )
                if input_hashes(config) != hashes:
                    raise ValueError("source inputs changed during the build")
                repository = PostgresKnowledgeExchangeRepository(session)
                directory = export_dump(
                    repository,
                    out_dir=Path(scratch),
                    dump_version=config.output_version,
                    private_key_pem=private_pem,
                    embedding_model_revision=config.embedding_model_revision,
                )
                manifest = verify_dump(
                    directory,
                    public_key_pem=public_pem,
                    expected_model_name=config.embedding_model_name,
                    expected_model_revision=config.embedding_model_revision,
                )
                if sum(part.rows for part in manifest.tables["document"]) == 0:
                    raise ValueError("build produced no exportable documents")
                documents = PostgresDocumentRepository(session)
                jurisdictions = {
                    SOURCE_REGISTRY[source.adapter].jurisdiction
                    for source in config.sources
                }
                if not any(
                    documents.search_documents_for_jurisdiction(j, limit=1)[0]
                    for j in jurisdictions
                ):
                    raise ValueError(
                        "build retrieval smoke check found no visible documents"
                    )
                provenance = {
                    "build_id": config.build_id,
                    "configuration_fingerprint": fingerprint,
                    "input_hashes": hashes,
                    "strategy": {
                        "name": config.strategy_name,
                        "revision": config.strategy_revision,
                    },
                    "embedding_model": {
                        "name": config.embedding_model_name,
                        "revision": config.embedding_model_revision,
                        "dimension": config.embedding_dimension,
                    },
                    "source_commit": os.environ.get(
                        "NORMLY_SOURCE_COMMIT", "development"
                    ),
                    "image_digest": os.environ.get(
                        "NORMLY_BUILDER_IMAGE_DIGEST", "unrecorded"
                    ),
                    "authenticated": False,
                }
                (directory / "build-provenance.json").write_text(
                    json.dumps(provenance, indent=2) + "\n"
                )
            if destination.exists():
                raise FileExistsError("output version already exists")
            directory.rename(destination)
        return destination
    finally:
        if engine is not None:
            engine.dispose()
        reservation.rmdir()
