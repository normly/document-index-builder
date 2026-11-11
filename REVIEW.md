# Review and testing

- Knowledge persistence: test migrated PostgreSQL/pgvector, all constraints/indexes, repeated upgrades, rights gating, lineage, withdrawal and user-table absence.
- Retrieval: compare checked-in OpenAPI with the app, test response semantics and jurisdiction non-disclosure, pagination/errors/rate limits, and a clean process without Docling.
- Exchange: verify signature/model/schema/checksums before mutation; exercise rollback, tombstones, masking and public export exclusions with synthetic data.
- Builder: fail closed on missing rights/configuration, isolate build identities, forbid overwrite, and prove partial failures cannot publish.
- Inspection: use the same parser configuration as ingestion, no database/embedding side effects, no implicit overwrite, and atomic local outputs.
- Images/tasks: check actual image contents, offline model paths, non-root ownership, read-only inputs and quoted paths. Consumer lifecycle needs real PostgreSQL concurrency/restart/update tests.
- Never claim a model, container, editor or release test ran when resources were unavailable. Only synthetic inputs belong in CI. Never publish from a verification run.
