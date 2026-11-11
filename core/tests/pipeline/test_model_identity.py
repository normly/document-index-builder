# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
import json
from types import SimpleNamespace

import pytest

from normly_core.embeddings import EmbeddingModel


@pytest.mark.parametrize(
    "identity", [None, {"name": "other/model", "revision": "wrong"}]
)
def test_unknown_local_weights_cannot_be_labeled_as_the_pinned_model(
    tmp_path, monkeypatch, identity
):
    if identity is not None:
        (tmp_path / "model-identity.json").write_text(json.dumps(identity))
    monkeypatch.setattr(
        "sentence_transformers.SentenceTransformer",
        lambda *a, **k: SimpleNamespace(get_sentence_embedding_dimension=lambda: 1024),
    )
    with pytest.raises(ValueError, match="identity"):
        EmbeddingModel(model_path=tmp_path)


def test_prepared_model_with_wrong_vector_dimension_is_refused(tmp_path, monkeypatch):
    (tmp_path / "model-identity.json").write_text(
        json.dumps(
            {
                "name": "intfloat/multilingual-e5-large",
                "revision": "3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3",
            }
        )
    )
    monkeypatch.setattr(
        "sentence_transformers.SentenceTransformer",
        lambda *a, **k: SimpleNamespace(get_sentence_embedding_dimension=lambda: 12),
    )
    with pytest.raises(ValueError, match="dimension"):
        EmbeddingModel(model_path=tmp_path)
