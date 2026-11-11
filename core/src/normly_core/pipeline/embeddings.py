# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
"""Compatibility imports for extracted adapters; implementation is shared."""
from normly_core.embeddings import EmbeddingModel, MODEL_NAME, MODEL_PATH_ENV_VAR

__all__ = ["EmbeddingModel", "MODEL_NAME", "MODEL_PATH_ENV_VAR"]
