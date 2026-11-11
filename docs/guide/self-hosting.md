# Run a populated retrieval service

Use a reviewed software release and separately trusted, immutable signed knowledge release. The runtime does not include Docling, source PDFs or ingestion. PostgreSQL is a separate persistent service. Do not use this setup to migrate an existing shared `web_app` database automatically.

## First start

1. Obtain signed runtime images and the release's OpenAPI contract from the project's authorized release channel. Local development can build `docker buildx bake -f docker-bake.hcl --load retrieval` instead; this does not publish anything. Always specify the bake file so image-only builds do not evaluate consumer Compose secrets.
2. Copy `.env.example` to private `.env`. Set a dedicated URL-safe random `NORMLY_POSTGRES_PASSWORD`, `NORMLY_KB_VERSION`, authorized `NORMLY_KB_BASE_URL`, and host path `NORMLY_KB_PUBLIC_KEY_FILE`. Provision the trusted public key separately from untrusted downloads. Production requires an immutable version, not `latest`.
3. Set `NORMLY_RETRIEVAL_IMAGE` to the verified published image digest for production. Do not rely on the local `:dev` tag there. Prepare encrypted persistent storage on authorized infrastructure and keep encryption keys outside it.
4. Run `docker compose up -d --wait`. Migration completes first, then an initializer downloads/verifies/imports the selected release in one transaction. Retrieval becomes ready only with the supported schema, exchange version and matching model revision.

The database and retrieval service have no host-published ports. Attach the trusted frontend/BFF proxy to the private Docker network named by `NORMLY_NETWORK_NAME` (default `document-index`) and use `http://retrieval:8000`. Do not expose forwarded-header-trusting retrieval directly to the Internet. HTTPS belongs on the trusted ingress. Accounts and chat do not receive knowledge database credentials.

## Restart and updates

Restart never silently replaces a populated volume or follows an updated `latest` alias. Initializers serialize through a PostgreSQL advisory lock. A different selected version on an existing volume is an error requiring an explicit update. A build-owned database is refused. A failed initialization rolls back and can be retried; no compatible import marker means no readiness.

Before an update, verify image/contract/exchange/model compatibility and the release signature. The currently supported combination is API `/v1`, exchange schema 1, e5 revision `3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3`, dimension 1024, migrations through `0002_build_identity`.

Verify without changing the database, then explicitly import through the prepared runtime:

```sh
docker compose run --rm --no-deps bootstrap \
  python -m normly_core.exchange verify --fetch VERSION
docker compose run --rm --no-deps bootstrap \
  python -m normly_core.exchange import --fetch VERSION
```

The bootstrap service carries the trusted-key mount, base URL and pinned model environment. Update `.env` to the imported immutable version afterward. Transactional import ensures a failed update leaves the old committed release in place; verify `/health/ready` and representative rights-filtered retrieval afterward. Changes to the model require a matching runtime and a deliberate deployment, not an environment-only model-ID substitution.

## Backups, rollback and withdrawal

Knowledge is reproducible from the signed exchange release, but operational tombstones and the current withdrawal state still matter. Keep protected backups and a versioned record of software/schema/knowledge/model identities. Never casually restore an older release over a newer schema, and never resurrect withdrawn text by exposing an old backup. Rehearse a supported restore into separate storage, apply the current legal withdrawal state, verify compatibility and only then switch traffic. There is no automatic destructive downgrade under this implementation.

User-state backups, citation reconciliation, notification generation and their retention/deletion journal belong to the coordinated `web_app` cutover plan. They are not included in a knowledge release. Do not share database volumes between build and consumer stacks; deleting a Compose volume is destructive and is not a routine restart step.
