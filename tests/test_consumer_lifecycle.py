# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path
from threading import Barrier

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from testcontainers.community.postgres import PostgresContainer

from normly_core.exchange.exporter import export_dump
from normly_core.exchange.signing import generate_keypair
from normly_core.graph.domain import LegalBasisCategory
from normly_core.graph.postgres.exchange import PostgresKnowledgeExchangeRepository
from normly_core.graph.postgres.repositories import (
    PostgresSourceRepository,
    PostgresDeliveryRepository,
    PostgresDocumentRepository,
    PostgresRightsRepository,
)
from normly_core.migrate import upgrade_to_head

REVISION = "3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3"


@pytest.fixture()
def release(tmp_path):
    with PostgresContainer("pgvector/pgvector:pg16", driver="psycopg") as source:
        url = source.get_connection_url()
        upgrade_to_head(url, Path("core").resolve())
        engine = create_engine(url)
        private, public = generate_keypair()
        key = tmp_path / "public.pem"
        key.write_bytes(public)
        with Session(engine) as session, session.begin():
            now = datetime.now(timezone.utc)
            s = PostgresSourceRepository(session).create_source(
                publisher="Synthetic",
                retrieval_path="file:///synthetic",
                legal_basis_category=LegalBasisCategory.A,
                jurisdiction="DE",
                reviewed_at=date.today(),
                responsible_person="Test",
            )
            d = PostgresDeliveryRepository(session).record_delivery(
                source_id=s.id,
                content_hash="sha256:synthetic-lifecycle",
                ingested_at=now,
            )
            document = PostgresDocumentRepository(session).create_document(
                origin_issuer="TEST",
                origin_number="1",
                edition="2026",
                part=None,
                delivery_id=d.id,
            )
            PostgresRightsRepository(session).classify(
                document_id=document.id,
                jurisdiction="DE",
                may_process=True,
                may_index_fulltext=False,
                may_cite_passages=False,
                may_export_free=True,
                legal_basis_reference="Synthetic test",
                classified_at=now,
                classified_by="Test",
                delivery_id=d.id,
            )
            directory = export_dump(
                PostgresKnowledgeExchangeRepository(session),
                out_dir=tmp_path,
                dump_version="2026.11.1",
                private_key_pem=private,
                embedding_model_revision=REVISION,
            )
        engine.dispose()
    return directory, key


@pytest.fixture()
def consumer_url():
    with PostgresContainer("pgvector/pgvector:pg16", driver="psycopg") as consumer:
        url = consumer.get_connection_url()
        upgrade_to_head(url, Path("core").resolve())
        yield url


def arguments(url, release):
    directory, key = release
    return dict(
        database_url=url,
        release_version="2026.11.1",
        base_url="http://localhost/unused",
        public_key_file=key,
        expected_model_revision=REVISION,
        release_dir=directory,
    )


def test_empty_initialization_restart_and_explicit_version_change(
    consumer_url, release
):
    from normly_core.exchange.bootstrap import initialize_knowledge_base

    kwargs = arguments(consumer_url, release)
    first = initialize_knowledge_base(**kwargs)
    second = initialize_knowledge_base(
        **{**kwargs, "release_dir": Path("/does-not-exist")}
    )
    assert first == second
    assert first.dump_version == "2026.11.1"
    with pytest.raises(ValueError, match="explicit"):
        initialize_knowledge_base(**{**kwargs, "release_version": "2026.11.2"})


def test_bad_signature_or_model_does_not_populate_database(consumer_url, release):
    from normly_core.exchange.bootstrap import initialize_knowledge_base
    from normly_core.exchange.importer import ImportRefused

    kwargs = arguments(consumer_url, release)
    with pytest.raises(ImportRefused):
        initialize_knowledge_base(
            **{**kwargs, "expected_model_revision": "wrong-model"}
        )
    signature = release[0] / "manifest.json.sig"
    signature.write_bytes(b"invalid signature")
    with pytest.raises(ImportRefused):
        initialize_knowledge_base(**kwargs)
    engine = create_engine(consumer_url)
    with Session(engine) as session:
        repository = PostgresKnowledgeExchangeRepository(session)
        assert repository.imported_version() is None
        assert not repository.has_documents()
    engine.dispose()


def test_two_initializers_share_one_import_generation(consumer_url, release):
    from normly_core.exchange.bootstrap import initialize_knowledge_base

    barrier = Barrier(2)

    def initialize():
        barrier.wait(timeout=10)
        return initialize_knowledge_base(**arguments(consumer_url, release))

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(lambda _: initialize(), range(2)))
    assert first == second


def test_existing_volume_cannot_restart_with_different_model(consumer_url, release):
    from normly_core.exchange.bootstrap import initialize_knowledge_base

    kwargs = arguments(consumer_url, release)
    initialize_knowledge_base(**kwargs)
    with pytest.raises(ValueError, match="model"):
        initialize_knowledge_base(**{**kwargs, "expected_model_revision": "different"})
