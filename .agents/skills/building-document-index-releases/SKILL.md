---
name: building-document-index-releases
description: Use when a contributor needs to ingest authorized sources into an isolated knowledge build, produce a signed knowledge release, or retry a refused build in this repository.
---

# Build a signed knowledge release

A data build is not an image build. It needs authorized sources, a dedicated
PostgreSQL database and a signing key. It does not authorize publication.

## Steps

1. Read `AGENTS.md`, `docs/guide/building-knowledge.md` and
   `docs/guide/knowledge-releases.md`. Confirm permitted source/storage use;
   public CI uses synthetic inputs only. Never read private keys into prompts.
2. Build the builder image using `building-document-index-images` if needed.
3. Prepare a local configuration based on `builds/example.json`. Its input
   directories refer to **container paths** under `/inputs`: the wrapper mounts
   the host input directory there. Keep credentials out of JSON and Git.
4. Select a dedicated experiment using `COMPOSE_PROJECT_NAME`, and supply
   `NORMLY_BUILD_POSTGRES_PASSWORD` through a private environment or `.env`.
   Use a URL-safe password. Each experiment needs separate database storage;
   never point the builder at the consumer/shared application database.
5. With a fresh output version and an explicitly provided signing-key path:

   ```sh
   COMPOSE_PROJECT_NAME=document-index-experiment-01 \
     bash scripts/build-knowledge .local/build.json \
       '/path/to/authorized/inputs' .local/releases '/path/to/private-key.pem'
   ```

   VS Code equivalent: **Document Index: Build knowledge release**. The wrapper
   starts build PostgreSQL and pins the resolved local builder image ID.
6. Require successful exit, signed manifest/parts, verification success and
   `build-provenance.json` in the selected version directory. Consult
   `docs/guide/releasing.md` for acceptance before promotion; merely finding
   files is not proof of signature validity. Provenance is informational and
   unsigned; the signed manifest is the trust authority.

## Common mistakes

| Situation | Correct action |
|---|---|
| Changed parser, image, configuration or inputs | Use fresh experiment storage; build identity refuses incompatible reuse. |
| Pending review, skipped/corrupt PDFs or no exportable documents | Resolve the cause; do not weaken the release gate. |
| Existing version/output or stale lock | Preserve it; investigate active jobs before any targeted cleanup. |
| Need to reset the experiment | Ask before deleting volumes or other persisted state. |

Do not create destinations concurrently: the documented narrow empty-directory
publication race remains. Keep real knowledge and signing operations within
authorized infrastructure. No push, upload or production change is implied.
