# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors

from __future__ import annotations

import argparse
import os
import sys

from pathlib import Path

from sqlalchemy.orm import Session

from normly_core.graph.postgres.repositories import PostgresSourceRepository

from normly_core.pipeline.adapters.baua import BauaAdapter

from normly_core.pipeline.adapters.dguv import DguvAdapter

from normly_core.pipeline.adapters.eur_lex import EurLexAdapter

from normly_core.pipeline.domain import SourceAdapter

from normly_core.pipeline.sources import resolve_source


def build_adapter(
    source: str,
    *,
    directory: Path,
    session: Session,
    docling_markdown_dir: Path | None = None,
) -> SourceAdapter:
    """
    Build the adapter for `source`, bound to its registry entry.

    The registry entry is resolved (and registered on first use) before the
    adapter exists at all: without it there is no `Source` row for a delivery to
    descend from, and no legal-basis category behind the ingestion.
    """
    registered = resolve_source(PostgresSourceRepository(session), source)

    if source == "eur-lex":
        return EurLexAdapter(
            directory=directory,
            source_id=registered.id,
            legislation_reference="2006/42/EC",
            docling_markdown_dir=docling_markdown_dir,
        )
    if source == "dguv":
        return DguvAdapter(
            directory=directory,
            source_id=registered.id,
            docling_markdown_dir=docling_markdown_dir,
        )
    if source == "baua":
        return BauaAdapter(
            directory=directory,
            source_id=registered.id,
            docling_markdown_dir=docling_markdown_dir,
        )
    raise ValueError(f"unknown source: {source!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m normly_core.pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    inspection = sub.add_parser("inspect")
    inspection.add_argument(
        "--source", choices=["baua", "dguv", "eur-lex"], required=True
    )
    inspection.add_argument("--input", type=Path, required=True)
    inspection.add_argument("--config", type=Path, required=True)
    inspection.add_argument("--output", type=Path, required=True)
    build = sub.add_parser("build")
    build.add_argument("--config", type=Path, required=True)
    build.add_argument("--output-directory", type=Path, required=True)
    build.add_argument("--signing-key-file", type=Path, required=True)
    ingest = sub.add_parser("ingest")
    ingest.add_argument("source", choices=["eur-lex", "dguv", "baua"])
    ingest.add_argument("--directory", type=Path, required=True)
    ingest.add_argument("--docling-markdown-dir", type=Path)
    sub.add_parser("backfill-document-embeddings")
    args = parser.parse_args(argv)
    if args.command == "inspect":
        from normly_core.pipeline.inspect import inspect_pdf

        try:
            output = inspect_pdf(
                source=args.source,
                input_path=args.input,
                config_path=args.config,
                output_dir=args.output,
            )
        except (ValueError, OSError):
            print(
                "inspection refused; check authorization, configuration and output path",
                file=sys.stderr,
            )
            return 1
        print(f"inspection: {output}")
        return 0
    database_url = os.environ.get("NORMLY_DATABASE_URL")
    if not database_url:
        print("NORMLY_DATABASE_URL environment variable is required", file=sys.stderr)
        return 1
    if args.command == "build":
        from normly_core.pipeline.build import run_build
        from normly_core.pipeline.build_config import load_build_config

        try:
            directory = run_build(
                load_build_config(args.config),
                database_url=database_url,
                output_dir=args.output_directory,
                signing_key_file=args.signing_key_file,
            )
        except (ValueError, OSError):
            print(
                "build refused; check configuration, permissions and local build diagnostics",
                file=sys.stderr,
            )
            return 1
        print(f"verified release: {directory}")
        return 0
    from sqlalchemy import create_engine
    from normly_core.pipeline.document_embedding import backfill_document_embeddings
    from normly_core.pipeline.runner import run_adapter

    engine = create_engine(database_url)
    try:
        with Session(engine) as session, session.begin():
            if args.command == "ingest":
                summary = run_adapter(
                    build_adapter(
                        args.source,
                        directory=args.directory,
                        session=session,
                        docling_markdown_dir=args.docling_markdown_dir,
                    ),
                    session,
                )
                print(
                    f"processed={summary.records_processed} failed={summary.records_failed}"
                )
                if summary.records_failed:
                    raise ValueError("partial ingestion")
            else:
                backfill_document_embeddings(session)
        return 0
    finally:
        engine.dispose()
