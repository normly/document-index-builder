---
name: running-document-index-retrieval
description: Use when a contributor needs to start the document-index retrieval service, import or update a prepared knowledge release, check readiness, or verify the repository locally without publishing.
---

# Run and verify retrieval

Consumers use prepared signed knowledge, not ingestion. Keep consumer storage
separate from build storage and keep database access private.

## Start or update

1. Read `AGENTS.md`, `docs/guide/self-hosting.md` and
   `docs/guide/releasing.md`. Confirm authorization before changing persisted
   data or starting operational services.
2. Use the retrieval image (no Docling). For a local image build, follow
   `building-document-index-images`. Production uses a verified image digest.
3. Prepare private `.env` configuration from `.env.example` without overwriting
   existing settings. Required inputs: consumer password, immutable knowledge
   version, authorized release base URL and a separately trusted public key.
   Never substitute a key obtained only from an untrusted release download.
4. From the repository root, when startup is authorized:

   ```sh
   docker compose up -d --wait
   docker compose ps
   docker compose exec -T retrieval python -c \
     "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=5).read().decode())"
   ```

   Migration precedes verified import, then retrieval readiness. Require ready
   status and the expected knowledge version; ports are private, not exposed on
   host localhost. A trusted proxy reaches `http://retrieval:8000` on its network.
5. A different version on existing storage requires the explicit verify/import
   procedure in the self-hosting guide. Restart is not an update. Model/schema
   mismatches are blockers; never delete storage to silence them.

## Local verification without publication

For checks rather than service startup, use `CONTRIBUTING.md` and
`docs/guide/releasing.md`. The contract check is:

```sh
uv run --no-sync python scripts/check-api-contract.py
```

Install locked test dependencies and explicitly prepare matching models before
offline inference tests. SQL tests need disposable PostgreSQL/pgvector via
Docker. Image tests require both built images and `RUN_IMAGE_TESTS=1`.
`tests/container_smoke.py` creates unique local synthetic projects and removes
its own volumes; confirm this scoped lifecycle test is wanted before running.

## Common mistakes

| Situation | Correct action |
|---|---|
| No host port 8000 | Check readiness inside the container/private network. |
| Existing volume/version mismatch | Follow explicit update/recovery, not volume deletion. |
| No model artifacts | Prepare them first; runtime tests must not download models. |
| Verification complete | Report commands and results; do not push/publish or claim real-source quality. |

Actual publication, GUI behavior, real-source rights/quality and production
encryption need separate authorization/evidence. Preserve user-data ownership
in `web_app`; this workflow does not execute its cutover.
