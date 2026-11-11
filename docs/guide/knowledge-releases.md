# Signed knowledge releases

The ADR-025 exchange format is unchanged: Parquet parts per knowledge table, `manifest.json`, and Ed25519 `manifest.json.sig`. The signature authenticates the exact manifest bytes; the manifest authenticates each part by checksum and row count. It records exchange schema version (currently 1), immutable dump version/time, source deliveries, model name(s), pinned model revision and vector dimension (1024). Exchange versions are not Alembic revisions.

Export/import run through knowledge repositories, never `pg_dump` as the distribution format. Export excludes missing/revoked classifications, withdrawn deliveries, licensed collections, commercially exploited catalogs and nonexportable content. Personal reviewer names become `normly maintainers`. User tables, rate counters, build review queues and import markers are not exchange tables.

Use `python -m normly_core.exchange --help` for export/import/verify/info/keygen/tombstone operations. `verify --from DIR --public-key KEY` needs the expected `NORMLY_EMBEDDING_MODEL_REVISION`, not a database or inference stack. Never trust a key delivered only alongside an untrusted release: provision the trusted public key separately. No production signing key is bundled. Key generation refuses overwrite; keep private keys offline or on authorized STACKIT infrastructure.

Before import, verify signature, supported schema, expected model identity/revision/dimension, paths, checksums and row counts. Import operates in one caller-owned transaction: commit only after success, otherwise roll back. Missing content is purged, identifier rows become tombstones and deliveries are withdrawn; this is not a merge that silently leaves withdrawn text readable. Empty releases cannot take down a populated instance without an explicit override.

Build and consumer databases are different: importing a public release into a build database overwrites private reviewer names with public role labels. Existing shared-schema user citation cleanup belongs to the separately planned web_app cutover, not this service.

Actual knowledge releases are immutable, separately calendar-versioned, and published only to the authorized STACKIT Object Storage route. Public source CI may create ephemeral synthetic releases, never process or publish the real corpus. A software release does not authorize data publication. Model/exchange compatibility must be checked before deployment and again before readiness.
