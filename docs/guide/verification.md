# Verification guide

Use this guide to select and run repeatable software checks. It describes
procedures, not the outcome of a particular branch or test run. Run-specific
evidence is kept separately in the [verification record](../verification-record.md).

## Principles

- CI uses synthetic inputs only. Private or real-source PDFs are local-only and
  may be processed only when their rights classification and test authorization
  permit it.
- Prepare pinned model artifacts explicitly. Runtime tests run offline and must
  not download models implicitly.
- Use disposable PostgreSQL/pgvector test databases for integration tests; do
  not point verification commands at operational databases.
- Verification does not publish software images, knowledge releases, or other
  artifacts. External publication and production checks require separate
  authorization.

## Standard local test suite

Install locked development dependencies and prepare the pinned models once:

```sh
uv sync --locked --all-packages --all-extras
uv run --no-sync python docker/prepare-models.py --kind all --output .local/models
```

Model preparation is the explicit step that may access the configured model
source. Then run the suite offline, using the prepared model directories:

```sh
HF_HUB_OFFLINE=1 \
  NORMLY_EMBEDDING_MODEL_PATH="$PWD/.local/models/multilingual-e5-large" \
  NORMLY_DOCLING_ARTIFACTS_PATH="$PWD/.local/models/docling" \
  uv run --no-sync pytest -q
```

The full suite includes disposable PostgreSQL/pgvector integration checks and
requires a Docker environment suitable for Testcontainers. See
[CONTRIBUTING](../../CONTRIBUTING.md) and [REVIEW](../../REVIEW.md) for the
development setup and required coverage. Run narrower tests with
`uv run --no-sync pytest <test-path> -q` when iterating, but report the
full-suite result separately. If a prepared model or service is unavailable,
record that prerequisite failure; do not describe those checks as passing.

## Targeted checks

- Check the API schema contract:

  ```sh
  uv run --no-sync python scripts/check-api-contract.py
  ```

- After building both local images, run the image boundary tests:

  ```sh
  docker buildx bake -f docker-bake.hcl --load builder retrieval
  RUN_IMAGE_TESTS=1 uv run --no-sync pytest tests/test_image_boundaries.py -q
  ```

- After the images are built, `uv run --no-sync python tests/container_smoke.py`
  rehearses an isolated synthetic build/import lifecycle. It creates and removes
  only its own uniquely named Docker projects and volumes. See
  [releasing](releasing.md) for the complete promotion and compatibility checks.

## Local real-PDF adapter checks

These checks are separate from CI and require the private `web-app-raw-data`
submodule, authorized local test PDFs, human-verified annotations, and prepared
offline Docling artifacts. Follow
[`web-app-raw-data/EXTRACTION_TESTS.md`](../../web-app-raw-data/EXTRACTION_TESTS.md)
to review and maintain the annotation data.

From the repository root, explicitly opt in:

```sh
NORMLY_DOCLING_ARTIFACTS_PATH="$PWD/.local/models/docling" \
RUN_REAL_PDF_TESTS=1 uv run --group dev --all-packages --all-extras \
  python -m pytest \
  core/tests/pipeline/test_real_pdf_annotations.py \
  core/tests/pipeline/test_real_pdf_extraction.py -q
```

Without `RUN_REAL_PDF_TESTS=1`, tests skip before reading private annotations or
PDFs. With opt-in, annotation shape is checked; draft data fails the human-review
guard, and Docling/adapter checks skip before parsing. Mark a case `verified`
only after checking its expectations against the rendered PDF. Never add these
PDFs or their extracted text to CI or public artifacts.

## Recording results

For each verification run, record the exact commands, pass/skip/failure counts,
model and database prerequisites, and external checks not performed. Distinguish
synthetic wiring checks from real-source evidence. Keep that run-specific record
separate from this procedure; see the current
[verification record](../verification-record.md).
