# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
import subprocess
import sys


def test_runtime_does_not_import_docling():
    result = subprocess.run([sys.executable, "-c", """
import sys
from normly_api.main import create_app
assert create_app().openapi()['paths']
assert not any(n == 'docling' or n.startswith('docling.') for n in sys.modules)
assert not any(n.startswith('normly_core.pipeline') for n in sys.modules)
"""], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_embedding_loader_requires_prepared_local_weights(monkeypatch):
    import pytest
    from normly_core.embeddings import EmbeddingModel

    monkeypatch.delenv("NORMLY_EMBEDDING_MODEL_PATH", raising=False)
    with pytest.raises(ValueError, match="local"):
        EmbeddingModel()
