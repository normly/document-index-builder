# Document Index Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract an independently released knowledge-base builder and stable retrieval runtime from `web-app-local_dev_tooling`, distributing populated knowledge bases as signed exchange releases.

**Architecture:** Builder and retrieval images share knowledge-only domain/repository code but have different dependencies. A builder uses an isolated PostgreSQL database and exports signed Parquet; consumers verify/import a pinned release into their own PostgreSQL and query it over HTTP. A separately approved follow-up coordinates the `web_app` database and client cutover.

**Tech Stack:** Python >=3.11, uv, SQLAlchemy/Alembic, PostgreSQL/pgvector, Docling, sentence-transformers, FastAPI, PyArrow, cryptography, pytest, Docker Compose. Reuse source lockfile/model pins; resolve changes explicitly rather than upgrading incidentally.

**Spec:** `docs/superpowers/specs/2026-11-11-document-index-extraction-design.md` (draft; approval required before implementation).

## Global Constraints

- No raw corpus, generated full text, signing secrets, or operational data in public Git, images, or GitHub CI. CI uses synthetic fixtures only.
- Operations, production knowledge storage, and publication stay on STACKIT; preserve the narrowly authorized European local-testing exception from the source policy.
- Every source needs a register entry and legal basis; missing rights classification fails closed. Preserve jurisdiction checks, lineage, idempotency, withdrawal, and licensed-publisher isolation.
- Public releases exclude user data and licensed collections and preserve ADR-025 export gating and personal-name masking.
- Persisted operational data is encrypted and keys stored separately, subject only to existing explicit local-test exceptions.
- Models are pinned and prepared during image preparation; no external model-provider requests at runtime or in CI. Preserve existing model-license restrictions.
- Preserve AGPL attribution and existing source notices. Reconcile the API's current Apache license metadata with the repository license; do not silently relicense copied code.
- Source checkout: `../web-app-local_dev_tooling`, inspected commit `41a3ce276505f2edd11bdb5ad0db1ae85acbed64`; do not delete or modify its work during extraction.
- No implementation or source deletion until the companion design and this plan are approved. No live database cutover under this plan.

## Review Focus

1. User-state coupling hidden inside copied domain/CLI/exchange code must not create accounts/chat tables or dependencies here (Tasks 1–2).
2. Corrupt, incompatible, or interrupted imports must not replace a working active release (Tasks 4 and 7).
3. A query embedding model differing from the release model must prevent readiness, not silently degrade search (Tasks 3–4).
4. Withdrawn/invisible records and personal names must not leak through alternate endpoints, export, or update paths (Tasks 3–4).
5. Existing volumes, concurrent initializers, and container restarts must not trigger repeated or destructive population (Task 7).

---

## Scope and file ownership

This is a staged extraction, not permission to remove the existing implementation. Each task produces a separately testable increment. Task 9 delivers the next migration design, not an unreviewed production cutover.

| Target | Responsibility |
|---|---|
| `core/src/normly_core/graph/`, `core/migrations/` | Knowledge-only domain, repositories, schema |
| `core/src/normly_core/embeddings.py` | Shared pinned query/document embedding implementation |
| `core/src/normly_core/pipeline/` | Source adapters, extraction, build orchestration |
| `core/src/normly_core/exchange/` | Signed release verification/import/export |
| `api/src/normly_api/`, `api/openapi.yaml` | Retrieval implementation and reviewed HTTP contract |
| `core/tests/`, `api/tests/`, `tests/` | Extracted regression, contract, build and deployment tests |
| `docker/python.Dockerfile`, `compose.yaml`, `compose.build.yaml` | Runtime images and separate consumer/build stacks |
| `docs/guide/`, `docs/adr/README.md` | Contracts, usage, release policy and decisions |
| `docs/superpowers/specs/`, `docs/superpowers/plans/` | Designs and implementation plans |

Keep source module names initially. Split large mixed files only along the knowledge/user boundary; do not redesign the whole domain during migration. At each commit, include copied notices and changed documentation. Commit commands below assume DCO sign-off is configured; never invent an identity.

### Task 1: Record the extraction boundary and regression inventory

**Files:** Create `docs/guide/extraction-map.md`, `docs/adr/README.md`, `AGENTS.md`, `CONTRIBUTING.md`, `REVIEW.md`.

**Interfaces:** Consumes source policies and actual import/caller/foreign-key graphs. Produces a table mapping each copied module, test, migration object, CLI command and API operation to move/retain/split, plus its owner.

- [ ] Record `git -C ../web-app-local_dev_tooling status --short` and `git -C ../web-app-local_dev_tooling rev-parse HEAD`; inspect any local changes relevant to extraction with the user before selecting their contents.
- [ ] Inventory source `graph/domain.py`, `postgres/{orm,repositories,exchange}.py`, `exchange/tables.py`, both mixed CLIs, migrations, API rate limiting, notifications and all `web_app` consumers. Record knowledge UUID references and code that queries them directly. Enumerate exact source test paths in the map; execution may not proceed with unmapped consumers.
- [ ] Write the split ADR as proposed: independent releases, separate databases, preserved exchange format, and no nested image building. List required amendments to source ADR-023/025/026 and SRS references rather than renumbering their existing decisions.
- [ ] Write repository-local contribution/review constraints derived from the source, preserving legal/security restrictions without pretending all web UI rules apply here.
- [ ] Review the map against `KNOWLEDGE_TABLES`, `USER_TABLES`, `PIPELINE_STATE_TABLES`, and `SYSTEM_TABLES`; every table and user-to-knowledge foreign key must have a disposition. This is a documentary gate, not a passing runtime test.
- [ ] Commit: `git add docs/guide/extraction-map.md docs/adr/README.md AGENTS.md CONTRIBUTING.md REVIEW.md && git commit -s -m "docs: define knowledge service extraction boundary"`.

### Task 2: Extract the knowledge-only persistence package

**Files:** Create root `pyproject.toml`, `uv.lock`; `core/pyproject.toml`, `core/alembic.ini`, `core/migrations/env.py`, `core/migrations/versions/0001_knowledge_baseline.py`; copy/split source `core/src/normly_core/graph/` and `migrate.py`; create `core/tests/graph/test_service_boundary.py`, `core/tests/test_migrate.py`; port mapped knowledge tests and fixtures.

**Interfaces:** Preserve source knowledge repository/domain signatures and `upgrade_to_head(database_url: str, core_dir: Path) -> None`. Only knowledge tables, identity review state, import state and explicitly API-owned operational tables may be created. Separate user-state repositories are not part of this package.

- [ ] Write boundary tests asserting all ADR-025 knowledge tables exist after migration, `account`, `chat_message`, `watchlist` and `notification` do not exist, and all remaining foreign keys target local tables. Assert a second upgrade is a no-op and percent-encoded database passwords survive configuration.
- [ ] Run `uv run --package normly-core pytest core/tests/graph/test_service_boundary.py core/tests/test_migrate.py -v`; expect failure until the workspace/schema exists. Missing project setup is not sufficient red evidence: rerun once fixtures load and confirm the missing behavior fails.
- [ ] Extract knowledge types/repositories with their existing names and SQL behavior. Build a new baseline reproducing knowledge constraints, vector indexes, extensions, and deletion behavior from the full source migration history; do not copy just the initial migration. Exclude user cleanup and notification generation. Give API rate-limit state its own local ownership rather than treating it as exported knowledge.
- [ ] Make `normly-core` base dependencies lightweight, with explicit `builder`, `retrieval`, and `dev` extras. Resolve the source's stale `normly-api` core version constraint against the new independently released workspace, retaining CPU wheel source restrictions and model pins.
- [ ] Run the boundary tests and all mapped graph tests against real pgvector PostgreSQL; expected PASS. Compare constraints/indexes with the extraction map, not only table names.
- [ ] Commit the workspace, knowledge code, baseline and tests: `git commit -s -m "refactor: extract knowledge persistence and schema"` after explicitly staging Task 2 files.

### Task 3: Extract retrieval and freeze the baseline HTTP contract

**Files:** Copy/split `api/src/normly_api/`, `api/tests/`, `api/pyproject.toml`; create `api/openapi.yaml`, `docs/guide/retrieval-api.md`, `api/tests/test_openapi_contract.py`, `api/tests/test_runtime_boundary.py`; create `core/src/normly_core/embeddings.py`; update API embedding imports.

**Interfaces:** Preserve `normly_api.main.create_app() -> FastAPI`, the actual existing `/v1` operations and response schemas. Shared `EmbeddingModel` preserves source `embed_query`/document embedding behavior. API server runtime cannot import Docling or user-state packages.

- [ ] Export the source app's normalized OpenAPI without running its model-loading lifespan; enumerate operation IDs, methods, paths, status codes and schemas. Save the reviewed baseline as YAML, with license metadata corrected to reflect copied code notices and repository policy.
- [ ] Add tests `test_openapi_matches_reviewed_contract` (normalized schema equality), `test_runtime_does_not_import_docling` (fresh process import), and port actual endpoint/rights/error/rate-limit tests. Include negative/oversized limits, `/search` route ordering, jurisdiction invisibility, and withdrawn text through segments/free export. Contract metadata changes are explicit, not blanket exclusions.
- [ ] Run `uv run --package normly-api pytest api/tests -v`; verify the new boundary checks fail before extraction is complete.
- [ ] Extract routers, serializers and knowledge-facing dependencies. Relocate query embedding code out of the pipeline package. Preserve rate-limit outcomes using API-owned state; do not accidentally require account tables. Document exact existing text/semantic ranking, pagination, filters, errors, and lack of independent search-mode selectors.
- [ ] Run the same suite with stub model unit tests and a separate pinned-model integration test. Compare observable responses with the source synthetic corpus; expect PASS without downloading models during tests.
- [ ] Commit explicitly staged Task 3 files with `git commit -s -m "feat: expose compatible retrieval contract"`.

### Task 4: Extract signed knowledge exchange without user-state coupling

**Files:** Copy/split `core/src/normly_core/exchange/` and `graph/postgres/exchange.py`; create/port `core/tests/exchange/`, including `test_service_boundary.py` and `test_import_atomicity.py`; create `docs/guide/knowledge-releases.md`.

**Interfaces:** Preserve ADR-025 `export`, `import`, `verify`, `info`, `fetch` behavior and core exchange repository signatures where knowledge-only. Retain existing manifest serialization/signature bytes and model checks. User deletion replay/backup and citation-FK cleanup are not local runtime responsibilities.

- [ ] Write synthetic round-trip and source-format compatibility tests: export/import preserves knowledge UUIDs; user tables/data and personal names never appear; bad signatures, checksums, exchange versions, model names/revisions/dimensions are refused; missing classifications and licensed collections are not exported.
- [ ] Add interrupted-import rollback and missing-row withdrawal tests. Assert an existing release remains unchanged on failure; text/embeddings disappear as required while tombstone identifiers survive. Test import does not call a user-table repository.
- [ ] Run `uv run --package normly-core pytest core/tests/exchange -v`; confirm boundary/atomicity tests fail against incomplete extraction.
- [ ] Extract knowledge-only exchange functions and CLI subcommands. Remove local dependencies on account/chat deletion replay; retain provenance and tombstone behavior. Keep build and consumer databases distinct, including the source warning against importing public releases into ingestion databases.
- [ ] Document the accepted manifest fields, signature trust roots and supported model/format combinations. Test an existing-format synthetic export from the source implementation as a golden compatibility fixture; never use real corpus fixtures or production signing keys.
- [ ] Run all exchange and graph tests; expect PASS, including failure-before-mutation assertions. Commit explicitly staged Task 4 files with `git commit -s -m "feat: support signed independent knowledge releases"`.

### Task 5: Extract ingestion and introduce isolated, reproducible build configurations

**Files:** Copy/split `core/src/normly_core/pipeline/` and mapped pipeline tests; create `pipeline/build.py`, `pipeline/build_config.py` under that package; create `core/tests/pipeline/test_build.py`, `test_build_config.py`, `builds/example.json`, `docs/guide/building-knowledge.md`.

**Interfaces:** Add `load_build_config(path: Path) -> BuildConfig` and `run_build(config: BuildConfig, *, database_url: str, output_dir: Path, signing_key_file: Path) -> Path`. Return the verified release directory. CLI: `python -m normly_core.pipeline build --config PATH --output-directory PATH --signing-key-file PATH`; database URL stays in `NORMLY_DATABASE_URL`.

- [ ] Write config tests for required fields from the design, unique build/output versions, invalid adapter/strategy/model settings, and unreadable inputs. Reject credentials in config; signing key contents are never logged. Initially accept only the extracted strategy revision.
- [ ] Write orchestration tests asserting migrate -> authorized ingestion -> export -> verify order, no publication after partial failures, idempotent repeated ingestion, refusal to overwrite an output version, and refusal to reuse a database belonging to another build ID. Use synthetic PDFs and stub embeddings by default.
- [ ] Run `uv run --package normly-core pytest core/tests/pipeline/test_build_config.py core/tests/pipeline/test_build.py -v`; expect the new commands/functions to be missing.
- [ ] Extract adapter behavior unchanged, including Docling Markdown tooling and rights gates. Strip user maintenance/admin/notification commands from the extracted CLI, retaining them in the source checkout. Implement config/build orchestration and a database build-identity marker; mark a build successful only after verification. Write outputs through a temporary directory and rename only when complete.
- [ ] Record hashes/configuration/source/image/model/strategy identity as release provenance. Preserve exchange compatibility: keep sidecar provenance informational unless covered by the signed manifest via a reviewed version-compatible extension; do not claim unsigned provenance is authenticated.
- [ ] Port offline Docling tests and run all pipeline tests. Add an opt-in prepared-model PDF integration test proving nonempty segments and correct embedding dimensions without network access. Expected PASS; document model resources required for this test.
- [ ] Commit explicitly staged Task 5 files with `git commit -s -m "feat: build isolated versioned knowledge artifacts"`.

### Task 6: Build distinct builder and retrieval images

**Files:** Create `docker/python.Dockerfile`, `.dockerignore`, `docker-bake.hcl`, `compose.build.yaml`, `.env.example`, `tests/test_image_boundaries.py`.

**Interfaces:** Docker targets `builder` and `retrieval`. Builder accepts Task 5's CLI, mounted read-only inputs/key, output directory and a build-database URL. Retrieval runs `normly_api.main:create_app` with the prepared query model and a consumer-database URL. No Docker socket or corpus in either image.

- [ ] Add image checks asserting retrieval has no importable Docling, both images run as non-root, no input/key/output directories enter image layers, and the offline model locations resolve. Ensure Docker build context excludes the raw-data submodule and local artifacts.
- [ ] Build draft targets and run `pytest tests/test_image_boundaries.py -v`; expect failures until dependency stages and exclusions are correct. Inspect image history and filesystem, not merely Dockerfile strings.
- [ ] Adapt the source Docker build's pinned CPU/model preparation stages. Install shared embedding dependencies in retrieval, Docling only in builder. Build-time fetching of pinned artifacts is allowed; inference/runtime external-provider fetching is not.
- [ ] Add a separate build Compose stack with persistent build PostgreSQL and a one-shot builder. Do not route ingestion into the consumer database. Document encrypted storage expectations and keep secrets out of the example configuration.
- [ ] Run `docker buildx bake builder retrieval` and image-boundary tests; expect PASS. Run one synthetic build with `docker compose -f compose.build.yaml run --rm builder` using documented mounts and prepared config; verify the emitted release.
- [ ] Commit explicitly staged Task 6 files with `git commit -s -m "build: separate builder and retrieval runtimes"`.

### Task 6a: Add single-PDF inspection and container-backed VS Code tasks

**Files:** Create `core/src/normly_core/pipeline/inspect.py`, `core/src/normly_core/pipeline/docling_config.py`, `core/tests/pipeline/test_inspect.py`, `core/tests/pipeline/test_docling_config.py`, `.vscode/tasks.json`, `scripts/inspect-pdf`, `scripts/build-knowledge`, `configs/docling.example.json`, `tests/test_developer_tasks.py`, `docs/guide/inspecting-pdfs.md`; modify `pipeline/cli.py`, `pipeline/docling_extraction.py`, `compose.build.yaml`, `.gitignore`, `.dockerignore`, `docs/guide/building-knowledge.md`.

**Interfaces:** Add `inspect_pdf(*, source: str, input_path: Path, config_path: Path, output_dir: Path) -> Path` returning a completed output directory. CLI: `python -m normly_core.pipeline inspect --source SOURCE --input PATH --config PATH --output PATH`. Shared configuration loading resolves only explicitly supported settings and feeds both inspection and ingestion. Configuration includes the source-register identity and processing authorization needed for fail-closed operation without PostgreSQL; reuse the existing rights rules, never invent an inspection bypass.

- [ ] Add `test_inspect_writes_markdown_native_json_effective_config_and_report`: assert four named files, input hash, effective settings and tool/model identity, using a synthetic PDF and stub converter. Add `test_inspect_does_not_connect_to_database_or_embed`, `test_inspect_rejects_missing_processing_permission`, `test_inspect_rejects_existing_output`, `test_inspect_cleans_partial_output_on_failure`, and `test_inspection_and_ingestion_use_identical_docling_settings`.
- [ ] Add config tests rejecting unknown/invalid settings, resolving defaults reproducibly and refusing missing source authorization. Run `uv run --package normly-core pytest core/tests/pipeline/test_inspect.py core/tests/pipeline/test_docling_config.py -v`; expect missing implementation failures. Factor existing parser settings without changing ingestion defaults.
- [ ] Implement the shared validated configuration, inspection module and CLI dispatch before database initialization. Reuse production extraction and Markdown export; serialize native Docling JSON. Write outputs atomically, record warnings/timing in `report.json`, never embed source text in logs. Retain ingestion's `--docling-markdown-dir` option.
- [ ] Add shell wrappers invoking the existing builder image via Compose: quote all paths, mount input/config read-only, expose no Docker socket, use host UID/GID and writable container cache/tmp directories. Inspection uses `run --rm --no-deps` and cannot start PostgreSQL. The full-release wrapper manages the separate build database and invokes Task 5's build command. Preserve underlying command exit codes.
- [ ] Add the three named VS Code tasks from the design. Inspection prompts for PDF, configuration, source and output directory; default output is `.local/inspection/example`. Tasks call wrappers and require a separately built builder image. Ignore `.local/` in Git and the image build context; never check in a real source path, PDF, generated text or secret. Document Linux/Docker Compose support and equivalent terminal commands.
- [ ] Add `tests/test_developer_tasks.py` to validate task labels/prompts and use a fake container command to assert argument boundaries for paths with spaces, mount permissions, UID/GID, no-dependency inspection and failure exit propagation. Run `pytest tests/test_developer_tasks.py -v` and the pipeline tests; expect PASS.
- [ ] Manually run `Document Index: Build builder image` then `Document Index: Inspect PDF` on an authorized synthetic PDF with prepared models. Confirm no PostgreSQL container starts, all four files are readable/deletable as the host user, native JSON opens, and Markdown previews in VS Code. Compare with ingestion using the same configuration. Record checks unavailable in a headless environment rather than claiming the editor was tested.
- [ ] Commit explicitly staged Task 6a files with `git commit -s -m "feat: add single PDF inspection developer tasks"`.

### Task 7: Deliver one-command consumer initialization and explicit updates

**Files:** Create `compose.yaml`, `core/src/normly_core/exchange/bootstrap.py`, `tests/test_consumer_lifecycle.py`, `docs/guide/self-hosting.md`; update API readiness in `api/src/normly_api/main.py` and tests.

**Interfaces:** `python -m normly_core.exchange.bootstrap` consumes `NORMLY_DATABASE_URL`, `NORMLY_KB_VERSION`, `NORMLY_KB_BASE_URL`, `NORMLY_KB_PUBLIC_KEY_FILE`, and the pinned model settings. Add `GET /health/ready`: 200 only when a compatible imported release and model are usable; otherwise 503 without secrets. Existing `/v1` shapes remain unchanged. Explicit updates use the retained exchange import command.

- [ ] Add lifecycle tests: empty volume initializes selected synthetic release; second start does not reimport; two initializers serialize safely; existing different release requires explicit update; missing trust key or invalid artifact prevents readiness. A mutable alias may be resolved for first initialization, but record its immutable version and do not refresh it on restart.
- [ ] Add tests for interrupted initialization/retry, successful compatible update, failed-update rollback, and startup with mismatched query-model revision. Use database-backed tests for lock behavior, not just mocks.
- [ ] Run `pytest tests/test_consumer_lifecycle.py -v`; expect missing bootstrap/readiness behavior.
- [ ] Implement a PostgreSQL advisory-lock-protected initialization path, using existing import transaction/verification. Compose orders migration, initialization, then retrieval readiness; PostgreSQL data stays on a volume and is not publicly exposed by default. Production configuration requires an immutable release version.
- [ ] Document fresh start, signature trust configuration, explicit update, database backup/restore, rollback compatibility checks and artifact caching. Never recommend importing an older release over a newer schema without a supported/tested restore path.
- [ ] Run lifecycle tests and a clean-volume `docker compose up --wait` smoke test with a synthetic release served locally. Confirm search/detail/segments responses, restart preservation and failure cases. Do not remove any pre-existing developer volumes during testing.
- [ ] Commit explicitly staged Task 7 files with `git commit -s -m "feat: initialize consumer knowledge releases safely"`.

### Task 8: Publish independent software and contract releases

**Files:** Create `.github/workflows/ci.yml`, `.github/workflows/images.yml`, `docs/guide/releasing.md`, `scripts/check-api-contract.py`; update `README.md` and `docs/guide/knowledge-releases.md`.

**Interfaces:** Software SemVer tags version this repository's builder/retrieval images and API-contract release. Calendar-versioned knowledge artifacts remain separately signed and published through the existing STACKIT distribution policy. No production credentials or actual corpus in GitHub Actions.

- [ ] Add a contract check that exits nonzero when the normalized app schema differs from `api/openapi.yaml`. Run it on an intentional temporary schema mismatch; expect failure, restore only that test modification, and rerun expecting success.
- [ ] Configure CI for boundary, graph, pipeline, exchange, API and synthetic lifecycle suites. Prepared models must not require CI runtime requests to external model providers. Keep expensive prepared-model checks explicit and required in release verification rather than silently skipping them.
- [ ] Adapt source signing/provenance/SBOM practices to the new repository identity. Confirm the actual remote/registry owner before choosing image publication paths; do not copy the source's signing identity or invent a registry namespace.
- [ ] Document the compatibility matrix (API major, exchange schema, runtime release, model revision/dimension), release promotion checks, and immutable knowledge publication. Publish the reviewed OpenAPI file with software releases. Signatures must bind to this repository's workflow.
- [ ] Validate workflow syntax, build targets and contract check locally; exercise release automation only in an authorized dry-run/test channel. Run the full relevant suite and report unavailable integration resources rather than claiming a production release occurred.
- [ ] Commit explicitly staged Task 8 files with `git commit -s -m "ci: release knowledge tooling independently"`.

### Task 9: Prepare the coordinated web_app cutover design and stop for approval

**Files:** Create `docs/superpowers/specs/2026-11-11-web-app-knowledge-cutover-design.md` and `docs/superpowers/plans/2026-11-11-web-app-knowledge-cutover.md` (use the actual writing date if later); update `docs/guide/extraction-map.md`. Do not edit the other checkout under this task.

**Interfaces:** Consumes the complete Task 1 inventory and the implemented/published API contract. Produces an implementation-ready follow-up with exact consumer files, replacement queries/operations, database migrations and test cases. No live migration is authorized by writing it.

- [ ] Trace every user-to-knowledge foreign key, direct repository query, notification job, citation lookup, watchlist operation, backup/restore script, and model dependency from the source. Verify all have a target disposition; preserve knowledge UUIDs and user state.
- [ ] Design replacement HTTP operations where the existing API does not support notification/batch needs. Require an explicit contract review before adding them; do not invent endpoint semantics during a mechanical move.
- [ ] Specify migrations removing cross-database foreign keys while preserving UUID identifiers and retention semantics. Cover withdrawn and unavailable documents, citation invalidation, notification update detection and duplicate suppression. Define how old citations referencing removed segment IDs are rendered without retained withdrawn text.
- [ ] Specify a backed-up, rehearsable cutover/rollback order, supported old/new combinations, user-data restore handling and downtime expectations. Include synthetic end-to-end tests proving frontend/chat/accounts/watchlists work with only HTTP knowledge access.
- [ ] List exact source ADR/SRS/architecture/deployment/CI amendments and removal order for old ingestion/API/shared knowledge code. Delete old code only after the new consumer integration and migration tests pass in the follow-up work.
- [ ] Commit the follow-up documents with `git commit -s -m "docs: plan coordinated web app knowledge cutover"`; request approval before executing that plan or changing `web_app`.

## Completion evidence and handoff

- [ ] Self-review each design requirement against Tasks 1–9; document deviations and their approvals.
- [ ] Report source revision, software image digests, model revisions, tested exchange/API versions, all test commands/results and checks not run.
- [ ] Demonstrate two isolated synthetic builds, one fresh consumer import, one explicit update, one failed-update rollback, and query compatibility with the pinned HTTP contract.
- [ ] Confirm no corpus/secret artifacts were added to Git and no source-checkout work was deleted.
- [ ] State status accurately: independently usable extraction complete; full `web_app` separation awaits the separately approved cutover.

## Plan self-review

Coverage: service/API ownership (1–3); exchange, rights and withdrawal (2–4); experimental isolated builds (5); lean consumer images (6); single-PDF inspection/shared parser configuration/VS Code tasks (6a); populated first start and update safety (7); independent versions and discoverable contracts (8); shared-schema/user-state hazards and source-spec amendments (1, 9). All five Review Focus items have owning tests. The only intentionally deferred implementation is the coordinated `web_app` cutover, whose design requires the complete extraction inventory and stable service contract.
