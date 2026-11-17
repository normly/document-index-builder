# Architecture decisions

## DI-001 — Independently released knowledge service

Status: accepted by the user's implementation request (2026-11-11).

`document_index` owns ingestion, the knowledge database and retrieval API. Build the builder and retrieval images independently of `web_app`; distribute populated knowledge as signed ADR-025 Parquet releases in STACKIT Object Storage. PostgreSQL stays a separate persistent service. No nested container builder and no data in public images.

Preserve existing `/v1` semantics and publish its OpenAPI contract. Consumers depend only on HTTP, not `normly_core` or knowledge SQL. Preserve ADR-006 repositories, ADR-025 exchange/rights/signatures and ADR-026 withdrawals. New knowledge-only migrations target empty databases, not the old combined application schema.

This supersedes ADR-023's single shared workspace/version for components extracted here. The coordinated `web_app` change must amend ADR-023, ADR-025/026's colocated-user assumptions, REQ-BUILD-002, REQ-GIT-001/005, registry references and architecture/deployment documentation. Original decision numbers remain owned by `web_app`; this index does not renumber them.

Rejected: embedding corpus in a database image (REQ-DIST-004 conflict), ingestion in consumer runtime (heavy/coupled), shared user/knowledge SQL (violates ownership).

## DI-002 — Data-driven real-PDF extraction tests

Status: accepted by the user's implementation request (2026-11-17).

Real-PDF extraction checks use one standard-family-agnostic local test harness. Private JSON annotation files identify the adapter family and its constructor options, exact source PDF, and selected or complete expected adapter outputs. A small explicit registry maps family keys to the existing adapters; shared assertions compare annotated Docling properties, records, sections, references, and anchor assignments. Real PDFs and source-derived text remain private and opt-in; CI uses synthetic fixtures only. Annotations derived from parser output remain drafts until human PDF validation.

Rejected: one test module per standard family (duplicates common checks and drifts as families are added), implicit plugin discovery (adds unnecessary indirection for the current adapter set), LLM pass/fail (non-deterministic), and full-document snapshots (brittle and broader than the reviewed expectations).
