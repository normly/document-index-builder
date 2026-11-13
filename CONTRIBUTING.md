# Contributing

The software is AGPL-3.0; preserve existing source notices and attribution. Source documents have separate rights. Never contribute real corpus material, generated document text, operational data, credentials or private signing keys.

Use an issue or approved design/plan to make behavior changes traceable. Agree on
changes to public contracts, schemas, processing rights and component ownership
before implementation. Work on an isolated feature branch and submit focused
pull requests. CI runs on pull requests; follow `REVIEW.md` and summarize checks
in the PR. Use Conventional Commit messages and DCO sign-off (`git commit -s`)
with your configured human identity.

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

## Working with AI

AI-assisted work is welcome within the repository's legal and safety boundaries:

- The human contributor is accountable for the change and must understand and
  verify the submitted work. AI reviews are advisory; decisions and approvals
  remain with people.
- Disclose AI use in the pull request and add `Assisted-by: <tool>` to the
  commit message when AI contributed. Never use `Co-Authored-By` for an AI tool;
  the DCO sign-off belongs to the human contributor.
- Do not put source documents, generated document text, licensed or partner
  material, operational data, credentials, secrets or personal data into AI
  prompts or third-party tools. Follow `AGENTS.md` and the applicable source
  rights.

For suspected security issues, do not open a public issue containing sensitive content. Contact repository maintainers privately. Do not use production data to reproduce issues.
