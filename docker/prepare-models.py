#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
"""Explicit build preparation only; never invoked by application startup."""

import argparse
import json
import os
from pathlib import Path
import sys

# In image preparation the pin module is copied beside this script. In local
# preparation use the source module directly without importing Docling.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core/src/normly_core"))
from model_artifacts import MODEL_NAME, MODEL_REVISION, DOCLING_MODEL_REVISIONS


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--kind", choices=["embeddings", "docling", "all"], default="all"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    from huggingface_hub import snapshot_download

    if args.kind in ("embeddings", "all"):
        if os.environ.get("E5_REVISION", MODEL_REVISION) != MODEL_REVISION:
            raise ValueError(
                "model build arguments must match the reviewed runtime pins"
            )
        directory = args.output / "multilingual-e5-large"
        snapshot_download(
            repo_id=MODEL_NAME,
            revision=MODEL_REVISION,
            local_dir=directory,
            ignore_patterns=[
                "onnx/*",
                "openvino/*",
                "pytorch_model.bin",
                ".eval_results/*",
                "*.md",
            ],
        )
        (directory / "model-identity.json").write_text(
            json.dumps({"name": MODEL_NAME, "revision": MODEL_REVISION}) + "\n"
        )
    if args.kind in ("docling", "all"):
        for key, repo in [
            ("layout", "docling-project/docling-layout-heron"),
            ("layout_onnx", "docling-project/docling-layout-heron-onnx"),
            ("tableformer", "docling-project/docling-models"),
        ]:
            snapshot_download(
                repo_id=repo,
                revision=DOCLING_MODEL_REVISIONS[key],
                local_dir=args.output / "docling" / repo.replace("/", "--"),
            )
        (args.output / "docling/model-revisions.json").write_text(
            json.dumps(DOCLING_MODEL_REVISIONS) + "\n"
        )


if __name__ == "__main__":
    main()
