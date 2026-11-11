# Contributing

The software is AGPL-3.0; preserve existing source notices and attribution. Source documents have separate rights. Never contribute real corpus material, generated document text, operational data, credentials or private signing keys.

Agree on changes to public contracts, schemas, processing rights and component ownership before implementation. Work on an isolated feature branch. Make focused commits with DCO sign-off (`git commit -s`) using your configured identity; disclose AI assistance in contributions where applicable.

Python is managed with uv. Each package owns tests; use prepared model artifacts for offline integration checks. Run the checks required by `REVIEW.md`, record commands and outcomes, and report unavailable checks honestly. Never substitute mocked SQLite tests for PostgreSQL/vector/transaction coverage.

```sh
uv sync --locked --all-packages --all-extras
uv run --no-sync python docker/prepare-models.py --kind all --output .local/models
HF_HUB_OFFLINE=1 \
  NORMLY_EMBEDDING_MODEL_PATH="$PWD/.local/models/multilingual-e5-large" \
  NORMLY_DOCLING_ARTIFACTS_PATH="$PWD/.local/models/docling" \
  uv run --no-sync pytest -q
```

Model preparation is an explicit build step that can access the pinned model provider. The tests and application runtime may not. `tests/test_image_boundaries.py` is explicitly enabled with `RUN_IMAGE_TESTS=1` after both images are built; the release check also runs `tests/container_smoke.py`. See `docs/guide/releasing.md` for the complete sequence. Authorized real-source canaries and the VS Code editor UI are separate manual checks; synthetic results must not be presented as those checks.

For suspected security issues, do not open a public issue containing sensitive content. Contact repository maintainers privately. Do not use production data to reproduce issues.
