# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
"""Initialize an empty consumer once; changing a populated instance is explicit."""

import os
from pathlib import Path
import re
import sys
import tempfile

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from normly_core.embeddings import MODEL_NAME, MODEL_REVISION
from normly_core.exchange.fetch import fetch_dump
from normly_core.exchange.importer import import_dump, ImportRefused
from normly_core.graph.domain import ImportRecord
from normly_core.graph.postgres.lifecycle import PostgresLifecycleRepository


def initialize_knowledge_base(
    *,
    database_url: str,
    release_version: str,
    base_url: str,
    public_key_file: Path,
    expected_model_revision: str,
    release_dir: Path | None = None,
) -> ImportRecord:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", release_version):
        raise ValueError("invalid knowledge version")
    if (
        os.environ.get("NORMLY_ENVIRONMENT") == "production"
        and release_version == "latest"
    ):
        raise ValueError("production requires an immutable knowledge version")
    public_key = public_key_file.read_bytes()
    engine = create_engine(database_url)
    try:
        with Session(engine) as session, session.begin():
            lifecycle = PostgresLifecycleRepository(session)
            current = lifecycle.lock_and_current()
            if current is not None:
                if lifecycle.ready_record(expected_model_revision) is None:
                    raise ValueError(
                        "existing release has an incompatible schema or model"
                    )
                if (
                    release_version != "latest"
                    and current.dump_version != release_version
                ):
                    raise ValueError(
                        "use an explicit verified import to change the knowledge version"
                    )
                return current
            if lifecycle.exchange.has_documents():
                raise ValueError(
                    "nonempty knowledge database has no import marker; explicit recovery required"
                )
            if expected_model_revision != MODEL_REVISION:
                raise ImportRefused(
                    "runtime does not support the requested model revision"
                )
            with tempfile.TemporaryDirectory(prefix="knowledge-import-") as scratch:
                directory = release_dir or fetch_dump(
                    base_url, release_version, Path(scratch), public_key_pem=public_key
                )
                record = import_dump(
                    lifecycle.exchange,
                    dump_dir=directory,
                    public_key_pem=public_key,
                    expected_model_name=MODEL_NAME,
                    expected_model_revision=expected_model_revision,
                )
                if (
                    release_version != "latest"
                    and record.dump_version != release_version
                ):
                    raise ImportRefused(
                        "downloaded release does not match requested version"
                    )
            return record
    finally:
        engine.dispose()


def main() -> int:
    try:
        record = initialize_knowledge_base(
            database_url=os.environ["NORMLY_DATABASE_URL"],
            release_version=os.environ["NORMLY_KB_VERSION"],
            base_url=os.environ["NORMLY_KB_BASE_URL"],
            public_key_file=Path(os.environ["NORMLY_KB_PUBLIC_KEY_FILE"]),
            expected_model_revision=os.environ["NORMLY_EMBEDDING_MODEL_REVISION"],
        )
    except Exception:
        # Never reflect credential-bearing URLs or document data in task logs.
        print(
            "knowledge initialization refused; check configuration, trust and compatibility",
            file=sys.stderr,
        )
        return 1
    print(f"knowledge version: {record.dump_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
