# Extraction inventory

## Evidence and ownership

Committed extraction source: `web-app-local_dev_tooling` at `41a3ce276505f2edd11bdb5ad0db1ae85acbed64`. Preflight found only untracked `.github/dependabot.yml`; it is excluded and untouched. Consumer base inspected by the coordinated planning session: `8306293011364c421861903c2809a8c7b13f9c2d`. Their 12 committed differences concern ingestion/Markdown tooling and related documentation/tests, not shared persistence/API/user state.

| Source relative path | Disposition | Target owner |
|---|---|---|
| `core/src/normly_core/graph/domain.py` | Split: knowledge types/protocols and rate limit only | document_index core |
| `core/src/normly_core/graph/postgres/orm.py` | Split knowledge/review/import/rate state; omit user models | document_index core |
| `core/src/normly_core/graph/postgres/repositories.py` | Split knowledge repositories and their helpers; omit account/chat/notification implementations | document_index core |
| `core/src/normly_core/graph/postgres/exchange.py` | Move; remove user citation FK detachment, retain tombstones | document_index core |
| `core/src/normly_core/pipeline/{adapters,domain,runner,identity,references,sources,work_assignment,docling_extraction,docling_markdown,document_embedding}.py` | Move without algorithm changes | builder |
| `core/src/normly_core/pipeline/embeddings.py` | Move implementation outside pipeline | shared core embeddings |
| `core/src/normly_core/pipeline/cli.py` | Split ingestion/backfill from user maintenance/admin commands | builder / retained web_app tools |
| `core/src/normly_core/exchange/` | Move knowledge exchange; retain user deletion journal/replay in web_app | document_index / user tools |
| `core/migrations/` (43 revisions) | Derive knowledge-only baseline from current schema, audit SQL-only indexes | document_index migrations |
| `core/src/normly_core/{admin,retention,notifications}/` | Retain; replace knowledge queries under separate cutover | web_app |
| `api/src/normly_api/` | Move all existing operations, errors and rate limiting | retrieval |
| `chat/src/normly_chat/{main,dependencies,synthesis,measure_usage}.py` | Retain orchestration; replace direct similarity/embedding usage with proposed passage API | web_app follow-up |
| `chat/src/normly_chat/{citation_labels,api_client,structural}.py`, `routers/{chat,sessions}.py` | Replace direct heading queries; preserve HTTP graph-first calls | web_app follow-up |
| `accounts/src/normly_accounts/routers/{watchlist,account_management,notifications}.py` | Retain user state; replace knowledge FK validation/export lookups | web_app follow-up |
| `frontend/src/app/api/documents/`, `frontend/src/lib/backend-urls.ts` | Repoint existing HTTP backend; never direct DB access | web_app follow-up |
| `scripts/normly-{deploy,backup,cleanup}`, `normly-env.sh`, `sync-to-vm.sh`, `deploy/systemd/` | Split knowledge/user lifecycle, restore, withdrawal and rollout ownership | coordinated follow-up |
| `compose.yaml`, `docker/`, `docker-bake.hcl`, `.github/workflows/`, `pyproject.toml`, `uv.lock` | Adapt code-only build/runtime stages; retain model pins; replace source signing identity | respective repository |

## Complete schema allocation

- Knowledge (all move): `source`, `delivery`, `work`, `document`, `document_designation`, `document_title`, `rights_classification`, `edge`, `segment`, `embedding`, `document_embedding`.
- Builder state: `identity_resolution_case`, `knowledge_build`; build identity is private operational state, never exchange data.
- Import state: `knowledge_base_import`.
- Retrieval operational state: `rate_limit_bucket`; it was grouped as user state but its production writer is API rate limiting. Never export it.
- Retained user state (all remain outside this repo): `publisher`, `account`, `account_session`, `account_google_identity`, `account_token`, `account_invitation`, `admin_audit_log`, `oauth_state`, `watchlist`, `notification`, `rights_notification_baseline`, `notified_edge`, `notified_retirement`, `deletion_log`, `chat_session`, `chat_message`, `chat_message_citation`, `llm_token_usage`, `llm_question_count`, `llm_budget_alert`.
- Each separate database owns `alembic_version`. User publisher organizations are not knowledge-source registrations.

Twelve user-to-knowledge FKs must be removed only in the coordinated cutover, preserving UUID values: `watchlist.work_id`; `notification.{work_id,trigger_edge_id,trigger_document_id}`; `rights_notification_baseline.{work_id,trigger_document_id}`; `notified_edge.{work_id,trigger_edge_id}`; `notified_retirement.{work_id,document_id}`; `chat_message_citation.{document_id,segment_id}`. Local user/message FKs remain. Identity review references are all local to the builder.

## CLI and HTTP inventory

Move ingestion, document-embedding backfill and knowledge exchange (`export`, `import`, `verify`, `info`, `tables`, `keygen`, `export-tombstones`, `import-tombstones`). Retain `cleanup-notifications`, `cleanup-user-data`, `notify-watchers`, `grant-admin`, user deletion export/replay in web_app. Add build and inspection commands without user dependencies.

Preserve GET operations: `/v1/documents`, `/v1/documents/search`, `/v1/documents/{document_id}`, document subpaths `/edges`, `/validity`, `/rights`, `/segments`, `/work`, and `/v1/export`. Verify exact operation IDs/query schemas against generated source OpenAPI in Task 3. No public write interface is introduced. Passage similarity, batch references, work validation and notification snapshots are proposed cross-repository additions, not part of the extraction's baseline contract.

## Regression file allocation

All following paths are relative to source `core/tests/graph/` and move: `test_source_repository.py`, `test_delivery_repository.py`, `test_document_repository.py`, `test_designation_and_title.py`, `test_document_work_id.py`, `test_delivery_find_and_document_find.py`, `test_edge_repository.py`, `test_rights_gate.py`, `test_jurisdiction_export.py`, `test_lineage_revocation.py`, `test_lineage_revocation_pipeline_tables.py`, `test_withdrawn_delivery_guard.py`, `test_embedding_repository.py`, `test_document_embedding_repository.py`, `test_segment_repository.py`, `test_segment_similarity_search.py`, `test_document_search.py`, `test_work_search.py`, `test_work_repository.py`, `test_work_structure.py`, `test_identity_resolution_case_repository.py`, `test_identity_resolution_work_merge.py`, `test_rate_limit_repository.py`. Port knowledge-only cases from `test_enum_columns.py`, `test_architecture.py`, `test_orm_migration_consistency.py`, `test_pgvector_extension.py`. Legacy revision-specific migration tests stay source-side; replace with new baseline parity/boundary tests.

Pipeline tests move from `core/tests/pipeline/`: `test_dguv_adapter.py`, `test_eur_lex_adapter.py`, `test_baua_adapter.py`, `test_docling_extraction.py`, `test_docling_markdown.py`, `test_docling_offline.py`, `test_references.py`, `test_runner.py`, `test_identity.py`, `test_work_assignment.py`, `test_runner_work_assignment.py`, `test_document_embedding.py`, `test_runner_document_embedding.py`, `test_embed_query.py`, `test_embeddings.py`, `test_end_to_end.py`, `test_architecture.py`; split CLI coverage and migrate imports for shared embeddings. Local real-corpus tests (`test_baua_full_pipeline_local.py`, `test_baua_adapter_real.py`) are not public CI fixtures. `baua_test_support.py` contains shared assertions and public heading identifiers, not source body text; retain it for synthetic checks. Generate PDF fixtures from invented text at test runtime (`synthetic_fixtures.py`) rather than copying source PDFs. User email/grant-admin tests stay in web_app.

Exchange tests move from `core/tests/exchange/`: `helpers.py`, `test_export_import.py`, `test_exchange_repository.py`, `test_embedding_roundtrip.py`, `test_published_role.py`, `test_retired_at_not_exported.py`, `test_signing.py`, `test_parquet_io.py`, `test_fetch.py`, `test_fetch_signature.py`, `test_manifest.py`, `test_verify.py`, `test_tombstones.py`. Split `test_takedown.py`, `test_cli.py`, `test_tables.py` to remove user references without deleting knowledge withdrawal assertions. `test_deletions.py` stays in web_app. All source `api/tests/test_*.py` move with endpoint behavior, adjusting only import/schema setup. User account/chat/notification/retention tests remain source-side.

## Coordinated cutover gate

The authoritative follow-up is on web_app branch `docs/document-index-cutover`: `docs/superpowers/specs/2026-11-11-document-index-cutover-design.md` and `docs/superpowers/plans/2026-11-11-document-index-cutover.md`. It inventories notification polling, citation/headings, rights context, backups/deletion-journal retention and all 12 FKs. Approval and new API contracts are required before removing old knowledge code or changing live user data. This extraction does not execute it.

The planning subsession created those drafts in `/home/tobi/.local/share/opencode/worktree/8d52b7/docs/document-index-cutover`. They remain owned by that branch, not duplicated into this repository. Required cross-repository additions include passage search, bounded reference/work resolution and generation-consistent notification snapshots; route proposals there are not implemented contracts here. The current `/v1` baseline and additive readiness route do not authorize the consumer cutover by themselves.

Clean isolated experiments inherit the source's UUID allocation behavior: exchange preserves the IDs of a particular build, but independently rebuilding an empty database is not a promise of the same UUIDs. Do not promote a fresh experimental identity lineage as a drop-in replacement for a user-linked corpus without the separately designed cutover/identity policy. Existing identifiers missing in an explicit import are retained as tombstones, not silently remapped.
