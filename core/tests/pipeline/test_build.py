# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
import json

import pytest
import sqlalchemy as sa

from normly_core.exchange.signing import generate_keypair
from .test_build_config import config_document


@pytest.fixture()
def build_db_url():
    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer("pgvector/pgvector:pg16", driver="psycopg") as container:
        yield container.get_connection_url()


def test_build_does_not_publish_partial_ingestion(build_db_url, tmp_path, monkeypatch):
    from normly_core.pipeline.build_config import load_build_config
    from normly_core.pipeline.build import run_build
    from normly_core.pipeline.runner import RunSummary

    source_dir = tmp_path / "inputs"
    source_dir.mkdir()
    path = tmp_path / "build.json"
    data = config_document(source_dir)
    path.write_text(json.dumps(data))
    config = load_build_config(path)
    key = tmp_path / "private.pem"
    key.write_bytes(generate_keypair()[0])
    monkeypatch.setattr(
        "normly_core.pipeline.build.build_adapter", lambda *a, **k: object()
    )
    monkeypatch.setattr(
        "normly_core.pipeline.build.run_adapter",
        lambda *a, **k: RunSummary(records_failed=1),
    )
    with pytest.raises(ValueError, match="failed|partial"):
        run_build(
            config,
            database_url=build_db_url,
            output_dir=tmp_path / "releases",
            signing_key_file=key,
        )
    assert not (tmp_path / "releases" / config.output_version).exists()


def test_build_refuses_existing_output_before_ingestion(tmp_path):
    from normly_core.pipeline.build_config import load_build_config
    from normly_core.pipeline.build import run_build

    path = tmp_path / "build.json"
    path.write_text(json.dumps(config_document(tmp_path)))
    config = load_build_config(path)
    out = tmp_path / "releases"
    (out / config.output_version).mkdir(parents=True)
    with pytest.raises(FileExistsError):
        run_build(
            config,
            database_url="unreachable",
            output_dir=out,
            signing_key_file=tmp_path / "not-needed",
        )


def test_release_build_refuses_silently_skipped_pdf(tmp_path):
    from normly_core.pipeline.docling_extraction import (
        strict_extraction,
        report_skipped_source,
    )

    with strict_extraction(), pytest.raises(ValueError, match="skipped"):
        report_skipped_source(tmp_path / "synthetic.pdf", ValueError("invalid PDF"))


def test_build_exports_verified_ids_and_refuses_different_build_identity(
    build_db_url, tmp_path, monkeypatch
):
    from normly_core.pipeline.build_config import load_build_config
    from normly_core.pipeline.build import run_build
    from normly_core.pipeline.sources import resolve_source
    from normly_core.graph.postgres.repositories import PostgresSourceRepository
    from normly_core.pipeline.domain import RawRecord
    from .test_runner import _FakeAdapter

    class FakeEmbeddingModel:
        def embed(self, text):
            return [1.0] + [0.0] * 1023

    def adapter(source, *, directory, session):
        registered = resolve_source(PostgresSourceRepository(session), source)
        record = RawRecord(
            source_id=registered.id,
            content_hash="sha256:synthetic-build",
            raw_designation="TRGS 900",
            raw_issuer="BAuA",
            raw_title="Synthetic test",
            full_text=None,
        )
        return _FakeAdapter(registered.id, [record])

    monkeypatch.setattr("normly_core.pipeline.build.build_adapter", adapter)
    monkeypatch.setattr(
        "normly_core.pipeline.runner.EmbeddingModel", FakeEmbeddingModel
    )
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    config_path = tmp_path / "build.json"
    data = config_document(inputs)
    config_path.write_text(json.dumps(data))
    key = tmp_path / "private.pem"
    key.write_bytes(generate_keypair()[0])
    output = run_build(
        load_build_config(config_path),
        database_url=build_db_url,
        output_dir=tmp_path / "releases",
        signing_key_file=key,
    )
    manifest = json.loads((output / "manifest.json").read_text())
    assert sum(e["rows"] for e in manifest["tables"]["document"]) == 1
    assert (output / "manifest.json.sig").is_file()
    assert (
        json.loads((output / "build-provenance.json").read_text())["authenticated"]
        is False
    )
    data.update(build_id="other-build", output_version="2026.11.2")
    config_path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="another build"):
        run_build(
            load_build_config(config_path),
            database_url=build_db_url,
            output_dir=tmp_path / "releases",
            signing_key_file=key,
        )
    assert not (tmp_path / "releases" / "2026.11.2").exists()


def test_build_refuses_a_database_with_no_exportable_documents(
    build_db_url, tmp_path, monkeypatch
):
    from datetime import datetime, timezone
    from normly_core.pipeline.build import run_build
    from normly_core.pipeline.build_config import load_build_config
    from normly_core.pipeline.runner import RunSummary
    from normly_core.pipeline.sources import resolve_source
    from normly_core.graph.postgres.repositories import (
        PostgresSourceRepository,
        PostgresDeliveryRepository,
        PostgresDocumentRepository,
        PostgresRightsRepository,
    )

    def nonexportable(source, *, directory, session):
        registered = resolve_source(PostgresSourceRepository(session), source)
        now = datetime.now(timezone.utc)
        delivery = PostgresDeliveryRepository(session).record_delivery(
            source_id=registered.id,
            content_hash="sha256:nonexportable",
            ingested_at=now,
        )
        doc = PostgresDocumentRepository(session).create_document(
            origin_issuer="TEST",
            origin_number="999",
            edition="2026",
            part=None,
            delivery_id=delivery.id,
        )
        PostgresRightsRepository(session).classify(
            document_id=doc.id,
            jurisdiction="DE",
            may_process=True,
            may_index_fulltext=False,
            may_cite_passages=False,
            may_export_free=False,
            legal_basis_reference="Synthetic nonexportable test",
            classified_at=now,
            classified_by="Test",
            delivery_id=delivery.id,
        )
        return object()

    monkeypatch.setattr("normly_core.pipeline.build.build_adapter", nonexportable)
    monkeypatch.setattr(
        "normly_core.pipeline.build.run_adapter",
        lambda *a, **k: RunSummary(records_processed=1),
    )
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    config = tmp_path / "build.json"
    config.write_text(json.dumps(config_document(inputs)))
    key = tmp_path / "private.pem"
    key.write_bytes(generate_keypair()[0])
    with pytest.raises(ValueError, match="exportable"):
        run_build(
            load_build_config(config),
            database_url=build_db_url,
            output_dir=tmp_path / "releases",
            signing_key_file=key,
        )
    assert not (tmp_path / "releases" / "2026.11.1").exists()
