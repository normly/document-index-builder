# Building knowledge releases

A builder populates its own PostgreSQL/pgvector database and writes a signed, verified Parquet release. It never builds another container image, ingests into a consumer database or publishes data automatically. Use only authorized source inputs; synthetic inputs are the only inputs allowed in public CI.

Start with [`builds/example.json`](../../builds/example.json). Input directories may be absolute container paths or relative to the configuration file. The supported initial strategy is `source-adapters` revision `1`, with registered adapters `baua`, `dguv`, `eur-lex`. Unknown fields/strategies/models, duplicate source entries and symlinked inputs are refused. Credentials and signing keys never belong in JSON configuration.

The supported initial embedding model is `intfloat/multilingual-e5-large` revision `3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3`, dimension 1024. A different model/strategy requires a deliberate implementation and compatibility change, not just editing an identifier. Prepare model weights before runtime. Set `NORMLY_EMBEDDING_MODEL_PATH` to local weights and `HF_HUB_OFFLINE=1`; use the pinned builder image for reproducible Docling artifacts. The preparation command writes `model-identity.json`; loading checks identity and actual vector dimensions. An existing local Hugging Face snapshot is also accepted only at the exact pinned repository/revision cache path. Arbitrary unlabeled local directories are refused rather than silently called e5.

The command is:

```sh
python -m normly_core.pipeline build \
  --config builds/example.json \
  --output-directory .local/releases \
  --signing-key-file /path/to/private-signing-key.pem
```

Pass `NORMLY_DATABASE_URL` through the environment and use an empty, dedicated build database. The migration runner locates the package's `core/` directory or `NORMLY_CORE_DIR`. Never point the builder at a production or shared web application database.

Each database is claimed by a build ID and a fingerprint of configuration plus input hashes, protected by a database advisory lock. Reusing another build's storage or changing that configuration/inputs is refused. A retry with the same inputs can reuse the same identity and idempotent deliveries. A different experiment needs a different database, not just a new output path. Consumer import markers also prevent accidental reuse.

Output versions are immutable. Existing destinations and concurrent output reservations are refused. Records failing processing or requiring identity/rights review, skipped/corrupt PDFs, changed inputs, empty builds and failed verification do not emit a completed release. Review and resolve inputs before retrying. A crash can leave a `.VERSION.lock` directory: confirm no builder is running before manually removing that specific reservation; never delete storage broadly.

`build-provenance.json` records build/configuration/input identities, strategy/model identity and optional `NORMLY_SOURCE_COMMIT` / `NORMLY_BUILDER_IMAGE_DIGEST`. It is informational and **not authenticated** by the unchanged ADR-025 manifest. Never use this sidecar as a trust or compatibility authority. The signed manifest remains authoritative. Promotion requires a recorded image digest/source revision, verified rights/export gates, and retrieval smoke/integration checks before authorized STACKIT publication.

The `ingest SOURCE --directory PATH --docling-markdown-dir PATH` command remains for explicit local diagnostics and review. It does not emit a public release; the optional Markdown contains source text and requires the same storage permissions as the inputs. User cleanup/admin/notification commands belong to `web_app`, not this builder.
