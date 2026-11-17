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

## Local real-PDF ingestion-to-retrieval acceptance

This is a separate, manual local acceptance procedure for checking that an
authorized source document survives the complete build, release, import, and
retrieval path. It is not the same as the real-PDF adapter tests above:
`RUN_REAL_PDF_TESTS` checks Docling and adapter output, not PostgreSQL persistence
or retrieval. The existing `tests/container_smoke.py` is also not a substitute;
it uses synthetic inputs only. There is currently no automated real-source
end-to-end runner.

### Before starting

- Use only a PDF and source collection explicitly authorized for this local test,
  with a registered adapter and the required rights classification. Follow the
  repository source policy: its current exception is limited to the explicitly
  authorized corpus and direct local-test artifacts on contributor-controlled
  European machines.
- Initialize the private `web-app-raw-data` submodule. Its PDF and reviewed
  extraction annotations can identify a test case; only `verified` annotations
  are an oracle for extraction. A draft case is not evidence of expected output.
- Record a small set of known queries, expected document identities, segment
  anchors, and jurisdictions in private test notes or the private submodule.
  The existing extraction-annotation JSON does not define retrieval expectations
  and is not, by itself, a retrieval test oracle.
- Build the pinned builder and retrieval images if needed. Keep inputs, outputs,
  per-test environment files, signing keys, and database storage under protected
  local storage such as ignored `.local/`; never commit or upload them.
- Choose unique build and consumer Compose project/network names, dedicated
  database passwords, a fresh release version, and a separately trusted public
  key. Do not reuse a build database as a consumer database.

### Run the acceptance check

1. Prepare a local build configuration for the registered adapter and the
   authorized input directory. Use a fresh build project and run
   `scripts/build-knowledge` as described in
   [Building knowledge](building-knowledge.md). It starts the dedicated builder
   PostgreSQL/pgvector database and writes the signed release to the selected
   local output directory. A successful build is required; pending review,
   skipped/corrupt PDFs, or failed release verification are stop conditions.
   For example, with the build password supplied through the private `.env`:

   ```sh
   COMPOSE_PROJECT_NAME=document-index-realpdf-build-01 \
     bash scripts/build-knowledge \
       .local/real-pdf/build.json \
       '/path/to/authorized/source-directory' \
       .local/real-pdf/releases \
       /path/to/build-signing-key.pem
   ```

2. Verify the release from its local directory with the expected pinned model
   revision and the public key provisioned separately from the release, for
   example:

   ```sh
   NORMLY_EMBEDDING_MODEL_REVISION=3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3 \
     uv run --no-sync python -m normly_core.exchange verify \
       --from .local/real-pdf/releases/VERSION \
       --public-key /path/to/trusted-knowledge.pub.pem
   ```

3. Start a **fresh, separate consumer database** and import that local release
   with `python -m normly_core.exchange import --from DIR` and the same
   separately trusted public key. For a local directory import, create an
   ignored `.local/real-pdf/from-local-release.yaml` override:

   ```yaml
   services:
     bootstrap:
       volumes:
         - ${LOCAL_KB_RELEASE:?set an absolute local release directory}:/release:ro
       command:
         - python
         - -m
         - normly_core.exchange
         - import
         - --from
         - /release
         - --public-key
         - /run/secrets/kb-signing.pub.pem
   ```

   Set up a private per-test env file based on `.env.example`, including a
   dedicated `NORMLY_POSTGRES_PASSWORD`, `NORMLY_KB_VERSION`, the trusted
   `NORMLY_KB_PUBLIC_KEY_FILE`, the absolute `LOCAL_KB_RELEASE` path, and a
   unique `NORMLY_NETWORK_NAME`. The base Compose file still requires
   `NORMLY_KB_BASE_URL` during configuration; set it to
   `https://invalid.example` because the override imports from disk and does not
   fetch from that URL. Set `NORMLY_KB_VERSION` to the release's exact version.
   Start Compose with a unique consumer project name and both files (replace the
   example project name for each run):

   ```sh
   docker compose --env-file .local/real-pdf/consumer.env \
     --project-name document-index-realpdf-consumer-01 \
     --file compose.yaml \
     --file .local/real-pdf/from-local-release.yaml \
     up -d --wait
   ```

   Compose runs migrations before the overridden bootstrap import, then starts
   retrieval only after import succeeds. Keep the retrieval service and database
   on this private local Compose network with no host-published ports. Do not
   publish the release just to make it downloadable for this test.
4. Require `/health/ready` to report the selected knowledge version. With no
   host-published port, call the API from a trusted client on the private network
   or from inside the retrieval container (as in
   [Self-hosting](self-hosting.md)). Use the same operations as a consumer:
   search with
   `GET /v1/documents/search?jurisdiction=JURISDICTION&q=QUERY`, then follow the
   returned `best_match.id` with
   `GET /v1/documents/{id}?jurisdiction=JURISDICTION` and read
   `GET /v1/documents/{id}/segments?jurisdiction=JURISDICTION`. URL-encode query
   values. Compare document identity, title, and expected section text
   against human-reviewed private expectations; also check that an unauthorized
   jurisdiction does not reveal the document or its segments. Record the queries
   and outcomes locally without copying source text into this repository.
5. Preserve the isolated database and release while results are under review.
   Remove only the specifically named test project/storage after confirming it
   contains no state that needs to be retained; never use a broad volume cleanup.

This procedure is opt-in and local-only. It does not authorize new sources,
licensed processing, CI use, release publication, or production operation.
Synthetic inputs remain the only inputs for public CI.

## Recording results

For each verification run, record the exact commands, pass/skip/failure counts,
model and database prerequisites, and external checks not performed. Distinguish
synthetic wiring checks from real-source evidence. Keep that run-specific record
separate from this procedure; see the current
[verification record](../verification-record.md).
