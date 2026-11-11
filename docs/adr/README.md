# Architecture decisions

## DI-001 — Independently released knowledge service

Status: accepted by the user's implementation request (2026-11-11).

`document_index` owns ingestion, the knowledge database and retrieval API. Build the builder and retrieval images independently of `web_app`; distribute populated knowledge as signed ADR-025 Parquet releases in STACKIT Object Storage. PostgreSQL stays a separate persistent service. No nested container builder and no data in public images.

Preserve existing `/v1` semantics and publish its OpenAPI contract. Consumers depend only on HTTP, not `normly_core` or knowledge SQL. Preserve ADR-006 repositories, ADR-025 exchange/rights/signatures and ADR-026 withdrawals. New knowledge-only migrations target empty databases, not the old combined application schema.

This supersedes ADR-023's single shared workspace/version for components extracted here. The coordinated `web_app` change must amend ADR-023, ADR-025/026's colocated-user assumptions, REQ-BUILD-002, REQ-GIT-001/005, registry references and architecture/deployment documentation. Original decision numbers remain owned by `web_app`; this index does not renumber them.

Rejected: embedding corpus in a database image (REQ-DIST-004 conflict), ingestion in consumer runtime (heavy/coupled), shared user/knowledge SQL (violates ownership).
