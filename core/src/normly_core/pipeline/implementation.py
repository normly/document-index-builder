# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
"""Bind reusable build storage to the implementation that produced its rows."""

import hashlib
from importlib.metadata import distributions
import json
import os
from pathlib import Path
import platform


def source_tree_digest(root: Path) -> str:
    if not root.is_dir():
        raise ValueError("builder implementation source directory is unavailable")
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        digest.update(path.read_bytes() + b"\0")
    return digest.hexdigest()


def implementation_identity(core_dir: Path) -> dict[str, str]:
    environment = sorted(
        (distribution.metadata.get("Name", "").lower(), distribution.version)
        for distribution in distributions()
    )
    environment.append((platform.python_implementation(), platform.python_version()))
    return {
        "source_commit": os.environ.get("NORMLY_SOURCE_COMMIT", "development"),
        "image_digest": os.environ.get("NORMLY_BUILDER_IMAGE_DIGEST", "unrecorded"),
        "code_sha256": source_tree_digest(Path(__file__).resolve().parents[1]),
        "migrations_sha256": source_tree_digest(core_dir / "migrations"),
        "environment_sha256": hashlib.sha256(
            json.dumps(environment).encode()
        ).hexdigest(),
    }
