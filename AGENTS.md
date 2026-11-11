# document_index — repository instructions

This AGPL repository owns document ingestion, knowledge persistence, signed knowledge releases and retrieval. `web_app` owns accounts, chat orchestration and user state. Keep their boundary HTTP-only; do not introduce account/chat tables here.

## Safety and rights

- Operational services, production knowledge, secrets and publication belong exclusively on STACKIT. GitHub may host source, synthetic CI and code-only images, not actual knowledge data.
- Never commit source PDFs, generated text, corpus snapshots or secrets, including in tests or image layers. Local inspection outputs belong in ignored `.local/` storage.
- Every source requires registration and a legal category. Rights classification is the sole processing gate; missing classification means refusal. Never scrape commercially exploited catalog collections.
- Preserve source lineage, jurisdiction-specific rights, publisher isolation, withdrawal and idempotency. Free exports contain neither licensed collections nor user data.
- Encrypt persisted operational data, logs and backups with separate keys. The source policy's narrow exception permits only the explicitly authorized limited corpus and direct local-test artifacts on contributor-controlled European machines; it does not authorize new sources, licensed processing, CI or public artifacts.
- Models must be open-weight with OSI-approved licensing and pinned revisions. Prepare models during image preparation; no external model-provider access at runtime or in CI.
- Keep inspection and production extraction on the same configuration implementation. Inspection is not a rights bypass.

## Engineering

Database operations go through repositories. Keep exchange schema independent of Alembic. A new baseline is for empty knowledge databases, not an automatic upgrade of the old shared application database.

Read `CONTRIBUTING.md`, `REVIEW.md`, the active design and implementation plan before changes. Use test-first development for behavior changes, real pgvector integration tests for SQL and transaction behavior, and retain copied SPDX/copyright notices. Do not modify or delete source-checkout work during extraction.

Write documentation/code in English, retaining established German domain terms. Record architectural changes in `docs/adr/README.md`; designs and plans live under `docs/superpowers/{specs,plans}/`.
