# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
"""Inspect a single explicitly authorized PDF, without database or embeddings."""

from dataclasses import asdict
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
import tempfile
import time
import warnings

from normly_core.pipeline.docling_config import parse_pdf_config, use_pdf_config
from normly_core.pipeline.docling_extraction import extract_document
from normly_core.pipeline.sources import SOURCE_REGISTRY
from normly_core.model_artifacts import DOCLING_MODEL_REVISIONS as MODEL_REVISIONS


def inspect_pdf(
    *, source: str, input_path: Path, config_path: Path, output_dir: Path
) -> Path:
    if output_dir.exists():
        raise FileExistsError("inspection output already exists")
    raw = json.loads(config_path.read_text())
    if not isinstance(raw, dict) or set(raw) != {
        "source",
        "input_sha256",
        "rights",
        "docling",
    }:
        raise ValueError(
            "inspection needs source, input_sha256, rights and docling configuration"
        )
    if source not in SOURCE_REGISTRY or raw["source"] != source:
        raise ValueError("source does not match a registered adapter")
    digest = sha256(input_path.read_bytes()).hexdigest()
    if raw["input_sha256"] != digest:
        raise ValueError("input hash differs from the explicitly authorized PDF")
    rights = raw["rights"]
    if not isinstance(rights, dict) or set(rights) != {
        "jurisdiction",
        "may_process",
        "legal_basis_reference",
    }:
        raise ValueError("missing processing classification")
    if (
        rights["may_process"] is not True
        or rights["jurisdiction"] != SOURCE_REGISTRY[source].jurisdiction
    ):
        raise ValueError("processing is not permitted for this source and jurisdiction")
    if (
        not isinstance(rights["legal_basis_reference"], str)
        or not rights["legal_basis_reference"].strip()
    ):
        raise ValueError("processing classification requires a legal basis")
    config = parse_pdf_config(raw["docling"])
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".inspection-", dir=output_dir.parent
    ) as temporary:
        staged = Path(temporary) / "result"
        staged.mkdir()
        started = time.monotonic()
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            with use_pdf_config(config):
                document = extract_document(input_path)
            markdown = document.export_to_markdown()
            native_json = document.model_dump_json()
        if sha256(input_path.read_bytes()).hexdigest() != digest:
            raise ValueError("input changed during inspection")
        (staged / "document.md").write_text(markdown, encoding="utf-8")
        (staged / "document.json").write_text(native_json, encoding="utf-8")
        (staged / "configuration.json").write_text(
            json.dumps(
                {
                    **raw,
                    "docling": asdict(config),
                },
                indent=2,
            )
            + "\n"
        )
        (staged / "report.json").write_text(
            json.dumps(
                {
                    "input_sha256": digest,
                    "elapsed_seconds": time.monotonic() - started,
                    "versions": {
                        name: version(name) for name in ("docling", "docling-core")
                    },
                    "model_revisions": MODEL_REVISIONS,
                    "warnings": [
                        {
                            "category": warning.category.__name__,
                            "message": str(warning.message),
                        }
                        for warning in captured
                    ],
                    "note": "Pinned image model revisions; custom artifact directories require operator verification.",
                },
                indent=2,
            )
            + "\n"
        )
        if output_dir.exists():
            raise FileExistsError("inspection output already exists")
        staged.rename(output_dir)
    return output_dir
