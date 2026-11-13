---
name: building-document-index-images
description: Use when a contributor needs to build or rebuild the document-index-builder Docker image or retrieval image locally.
---

# Build the Docker images

An image contains software and prepared model weights, not a populated knowledge
database. Building the builder does not ingest documents or start PostgreSQL.

## Steps

1. Read `AGENTS.md` and `docs/guide/releasing.md` from the repository root.
2. Check Linux, Docker Engine, Compose and buildx availability. Run commands
   from the repository root. No host Python environment or database credentials
   are needed for an image-only build.
3. Build the requested target, not the consumer stack:

   ```sh
   REGISTRY= PUSH=0 docker buildx bake -f docker-bake.hcl --load builder
   ```

   Use `retrieval` instead of `builder` for the query service, or specify both
   targets when both are needed. Model downloads belong to image preparation;
   application runtime must remain offline. Clearing `REGISTRY` selects the
   documented local tags even if the shell has release variables configured.
4. Confirm successful exit and inspect the requested local image:

   ```sh
   docker image inspect normly/document-index-builder:dev
   ```

   Retrieval's local tag is `normly/document-index-retrieval:dev`. Record which
   targets actually built; do not equate an image build with a verified release.

## Common mistakes

| Situation | Correct action |
|---|---|
| Bare bake asks for consumer secrets | Specify `-f docker-bake.hcl`. |
| User wants Markdown for one PDF | Next read `inspecting-document-index-pdfs`, not full ingestion. |
| User wants a populated knowledge release | Read `building-document-index-releases`. |
| Publication suggested as verification | Do not push images or run publication without authorization. |

For image-content checks, follow `docs/guide/releasing.md`. Keep PDFs, outputs
and keys out of the Docker context and public CI.
