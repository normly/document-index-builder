# Document index extraction design

Status: approved for implementation by the user's request to implement this plan (2026-11-11). The coordinated `web_app` cutover remains a separate approval gate.

## Intent

Make knowledge-base construction independently testable and versioned. Experiment with parsing, chunking, embeddings, and indexes without coupling their releases to the consumer application. Keep `web_app` lean: consumers run retrieval against an already populated knowledge base, not ingestion.

`document_index` owns ingestion, knowledge persistence, exchange artifacts, and the retrieval service. `web_app` owns the frontend, accounts, chat orchestration, and user state. HTTP is the boundary; consumers do not import server packages or query knowledge tables.

## Source and evidence

Extract from `../web-app-local_dev_tooling`, inspected at commit `41a3ce276505f2edd11bdb5ad0db1ae85acbed64`. Capture its working-tree status before implementation; a commit ID alone does not capture uncommitted changes. Do not modify or delete source-checkout work as part of copying.

Relevant source paths:

- `core/src/normly_core/pipeline/`: adapters, Docling extraction, document/segment embeddings, identity resolution, runner, and mixed-purpose CLI.
- `core/src/normly_core/graph/{domain.py,postgres/}`: knowledge and user models/repositories currently mixed together.
- `core/src/normly_core/exchange/`: signed Parquet exchange, currently also contains user-deletion commands.
- `core/migrations/`: shared knowledge/user migration history.
- `api/src/normly_api/`: existing retrieval endpoints, schemas, errors, and rate limiting.
- `chat/src/normly_chat/api_client.py`: existing HTTP consumer.
- `docs/adr/README.md`: ADR-006, ADR-021, ADR-023, ADR-025, ADR-026.
- `docs/srs/03-requirements.md`: REQ-BUILD-001/002, REQ-DIST-002/004, REQ-GIT-001/005.

## Approaches

1. **Data-bearing database image:** simple distribution, but large private/data-bearing images, initialization and volume-update complexity; conflicts with REQ-DIST-004's data-independent images. Not selected.
2. **Signed versioned snapshot plus runtime images:** selected by the user. Software and knowledge releases are independent, the consumer imports a prepared release, and existing ADR-025 tooling can be retained.
3. **Ingestion inside the consumer stack:** keeps everything together but defeats the lean-consumer and independent-build goals. Not selected.

## Deliverables and topology

```text
Authorized local/STACKIT inputs + pinned build configuration
    -> builder image -> isolated build PostgreSQL
    -> signed Parquet knowledge release + manifest

Knowledge release -> verify/import -> consumer PostgreSQL
                                        ^
                                   retrieval API <- web_app
```

Build the builder and retrieval images here. PostgreSQL runs separately with persistent storage. No nested image builder or mounted Docker socket is required. The builder constructs a database and exports data; it does not build another container image.

Consumers receive a Compose setup with PostgreSQL, migration/import one-shots, and retrieval. An empty instance imports a selected release automatically before becoming ready. Existing volumes are not silently replaced, and restart does not follow a moving `latest` alias. Updates are explicit and verified before mutation. Production deployment pins immutable artifact versions.

### Packages and dependency boundaries (proposal)

Preserve `core/` and `api/` and their `normly_core`/`normly_api` import names during extraction to minimize changes. Keep only knowledge-domain and pipeline-state functionality in the extracted core. Split dependencies so the retrieval image includes the query embedding model but neither Docling nor its PDF-processing stack. Move shared embedding code to `core/src/normly_core/embeddings.py`, outside `pipeline/`.

Retain repository-layer persistence. Start a knowledge-only migration baseline for new, separate databases; do not replay shared migrations that create user tables. Migrating an existing live installation is a distinct, backed-up cutover, not an automatic baseline upgrade.

### Two contracts

1. **HTTP retrieval contract:** `api/openapi.yaml` is the reviewed, versioned artifact; `docs/guide/retrieval-api.md` explains semantics, examples, compatibility, and errors. Tests compare normalized FastAPI OpenAPI output with the checked-in contract and exercise real responses. Publish the contract with runtime releases. Consumers pin a supported contract release, not a branch URL. Generating clients is optional, not a first-release requirement.
2. **Exchange/runtime compatibility:** preserve ADR-025's Parquet tables, signed manifest, exchange schema version, model name and pinned revision, dimension, checksums, and row counts. Keep exchange-schema version independent of Alembic. Add signed optional build provenance compatibly or explicitly version the exchange format; never silently change signed-manifest parsing rules. Runtime compatibility must be checked against actual supported format/model/schema combinations, not inferred solely from a SemVer range.

Capture the existing `/v1` surface before changing it: document lookup/search/detail, work operations, edges, validity, rights, segments, and free export. Preserve query validation, pagination, jurisdiction gating, non-disclosure, and rate-limit behavior. Inventory the actual operations and their callers rather than assuming every router is read-only.

The current document search combines text matching and semantic candidates. Do not promise independent keyword/semantic mode selectors or new chunk-search endpoints until they have been designed and tested. Stable API does not mean identical rankings across experimental knowledge builds; document guarantees and permit ranking changes within them. Each API instance serves one active build/model combination; incompatible experiments use separate databases and runtimes.

### Builder and release provenance (proposal)

Use a validated JSON configuration with `build_id`, `output_version`, `sources` (adapter and input directory), `embedding_model` (name, revision, dimension), and `strategy` (name and revision). Source registration and rights classification remain prerequisites, not configurable bypasses. Record input hashes, source commit, image digest, strategy, and model identity in build provenance. A build ID identifies an isolated attempt; a published output version is immutable.

Initially expose the existing adapter/strategy implementation only. Reproducible named configurations and isolated build databases make comparison possible without first inventing a plugin framework. Do not claim bit-identical parsing or model outputs without evidence. Release promotion requires success of ingestion, signature/format verification, and retrieval smoke tests. Partial failures do not silently become public releases.

### User-data separation and coordinated cutover

The source `exchange/tables.py` explicitly groups knowledge, user, pipeline, and import-state tables. User citations, watchlists, and notifications have foreign keys into knowledge rows. Both the pipeline and exchange CLIs include unrelated user operations. Rate limiting also uses persistence.

Do not copy all of `core` or drop the old API and shared schema blindly. Extract knowledge functionality and API-owned operational state only; retain account/chat/notification maintenance in `web_app`. Preserve stable knowledge UUIDs in exchange artifacts. Cross-database references must become application-level identifiers with missing/withdrawn handling; they cannot retain physical foreign keys across databases.

Before changing `web_app`, produce and approve a separate cutover design/plan from a complete caller and foreign-key inventory. It must specify replacement notification queries, citation/withdrawal handling, user-data backup/restore, knowledge update detection, and rollback. This extraction plan creates the independently usable service; it does not authorize a destructive live migration. The complete repository split is not finished until that follow-up integration passes.

### Single-PDF inspection and local developer tasks

The builder image also supports inspecting one PDF without a database, chunking, embedding generation, or release publication. This is a second command in the same image, not another image target. Reuse the production Docling extraction and configuration handling so experiments transfer to ingestion. Preserve the existing ingestion-time `--docling-markdown-dir` capability as well.

Proposed inspection CLI: `python -m normly_core.pipeline inspect --source baua --input /inputs/example.pdf --config /configs/docling.json --output /outputs/example`. The configuration selects supported Docling settings; reject unknown settings rather than ignoring them. Source registration and processing permission checks still apply without a database, using a validated source/authorization configuration, never an implicit permission inferred from a filename or adapter. Initially scope this to one PDF per invocation.

Write `document.md`, native Docling `document.json`, `configuration.json` containing effective settings, and `report.json` containing input hash, tool/model revisions, timing and warnings. Do not overwrite an existing output directory implicitly. Keep outputs local, untracked, and subject to the same source-content storage restrictions as ingestion artifacts.

Provide checked-in `.vscode/tasks.json` tasks named `Document Index: Build builder image`, `Document Index: Inspect PDF`, and `Document Index: Build knowledge release`. The inspection task prompts for a PDF path, configuration path, source adapter and output directory (default `.local/inspection/example`). Mount input/configuration read-only and output writable; run with the developer's UID/GID so generated files are not root-owned. Tasks invoke documented scripts/Compose commands, not duplicated parsing logic. The inspection task uses an already built image and never starts PostgreSQL; the full-build task manages the separate build stack. Docker with Compose is the local prerequisite; no host Python environment is required for these tasks.

The developer runs Terminal → Run Task → Document Index: Inspect PDF, then opens the emitted Markdown using VS Code's preview. Adjust settings and rerun with a fresh output directory. Document equivalent terminal commands, mount/path rules (including paths with spaces), offline model preparation and cleanup. No custom inspection UI or batch-comparison framework is included.

## Invariants

- No raw corpus, generated full text, signing secrets, or operational data in public Git, images, or GitHub CI. CI uses synthetic fixtures only.
- Operations, production knowledge storage, and publication stay on STACKIT; preserve the narrowly authorized European local-testing exception from the source policy.
- Every source needs a register entry and legal basis; missing rights classification fails closed. Preserve jurisdiction checks, lineage, idempotency, withdrawal, and licensed-publisher isolation.
- Public releases exclude user data and licensed collections and preserve ADR-025 export gating and personal-name masking.
- Persisted operational data is encrypted and keys stored separately, subject only to existing explicit local-test exceptions.
- Models are pinned and prepared during image preparation; no external model-provider requests at runtime or in CI. Preserve existing model-license restrictions.
- Preserve AGPL attribution and existing source notices. Reconcile the API's current Apache license metadata with the repository license; do not silently relicense copied code.

## Documentation and release decisions

Use the existing `docs/superpowers/specs/` and `docs/superpowers/plans/` convention. Add `docs/adr/README.md` for the new decision and `docs/guide/` for operational documentation. Do not copy the entire web application specification as if it described this repository.

Propose independent software SemVer here and existing calendar-versioned knowledge releases. Explicitly amend ADR-023's shared release/workspace rule and repository-specific REQ-BUILD-002/REQ-GIT-001/005 references in a coordinated `web_app` change. Retain ADR-025 format/distribution and ADR-026 withdrawal intent; document adaptations required when user state is no longer colocated.

## Non-goals

No new search algorithm, source acquisition, scraping, commercial-content rights change, arbitrary strategy plugins, hosted ingestion API, client-code generation mandate, or automatic destructive production migration. No ingestion in the consumer runtime.

## Acceptance

1. Build a signed synthetic release using the builder and a separate build database.
2. Start an empty consumer stack; it imports the selected release and exposes compatible `/v1` retrieval without Docling or source files.
3. A second build configuration can produce a separate release without modifying or releasing `web_app`.
4. Invalid signatures, checksums, exchange versions, or model revisions are rejected before changing the active database.
5. Compatible explicit updates preserve IDs and honor removals/withdrawal; failed updates leave the old release usable.
6. Documentation identifies the API contract, exchange contract, supported combinations, and remaining `web_app` cutover gate.
7. A developer can inspect one authorized PDF using a VS Code task, without PostgreSQL or host Python, and inspect Markdown/native JSON alongside the effective production-parser configuration.
