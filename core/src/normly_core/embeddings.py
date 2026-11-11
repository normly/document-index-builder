# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors

from __future__ import annotations

import os
from pathlib import Path

MODEL_NAME = "intfloat/multilingual-e5-large"

#: Points the model loader at pre-provisioned weights on local disk.
MODEL_PATH_ENV_VAR = "NORMLY_EMBEDDING_MODEL_PATH"


class EmbeddingModel:
    """
    The local embedding model. Inference never leaves the machine.

    Weights must be prepared before runtime. No model-ID fallback or network
    download is allowed, including in development and CI. Importing the domain
    or generating API schemas does not import the inference stack.
    """

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        *,
        model_path: str | Path | None = None,
    ):
        self._model_name = model_name
        resolved_path = model_path if model_path is not None else os.environ.get(
            MODEL_PATH_ENV_VAR
        )
        if not resolved_path or not Path(resolved_path).is_dir():
            raise ValueError("a prepared local embedding model directory is required")
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(str(resolved_path), local_files_only=True)

    def embed(self, text: str) -> list[float]:
        # e5 models are trained with an instruction prefix; "passage: " is the
        # documented convention for indexing content (as opposed to "query: " for
        # search queries issued against the index).
        prefixed = f"passage: {text}"
        vector = self._model.encode(prefixed, normalize_embeddings=True)
        return vector.tolist()

    def embed_query(self, text: str) -> list[float]:
        # "query: " is e5's documented instruction prefix for search queries,
        # as opposed to "passage: " for indexed content -- same model, same
        # vector space, different prefix so the model can tell which role the
        # text plays.
        prefixed = f"query: {text}"
        vector = self._model.encode(prefixed, normalize_embeddings=True)
        return vector.tolist()
