# Independent software releases

Software in this repository has its own SemVer cycle; `core` and `api` share that software version here, independently of `web_app`. The HTTP API major remains `/v1`; its version is not a knowledge calendar version. A release tag must be `vX.Y.Z` and match both package versions. Update the lockfile deliberately, not incidentally while building.

The reviewed contract is `api/openapi.yaml`, published with tagged software releases. Run `uv run --no-sync python scripts/check-api-contract.py`; a schema mismatch fails the build. Changes to response shapes, rights or ranking semantics need review even if generated schema output still matches. Keep `/v1` consumer compatibility and the guide aligned.

## Verification before promotion

- Install locked extras and prepare pinned models using `docker/prepare-models.py` during build preparation; tests run with `HF_HUB_OFFLINE=1` and explicit local model paths.
- Run the complete synthetic core/API/developer/lifecycle suite against disposable PostgreSQL/pgvector. No real source data, private raw-data submodule or operational credentials belong in CI.
- Build both images with `docker buildx bake -f docker-bake.hcl --load builder retrieval`; run `RUN_IMAGE_TESTS=1 uv run --no-sync pytest tests/test_image_boundaries.py`.
- Run `uv run --no-sync python tests/container_smoke.py` after building both images. It rehearses two isolated synthetic builds, fresh consumer startup, restart, explicit update and bad-signature rejection, then removes only its newly created, unique Docker projects/volumes. It refuses a remote Docker endpoint or an existing matching project. Check representative keyword/text/semantic, document and segment reads with jurisdiction restrictions. Editor UI behavior needs a separate manual VS Code check.
- Review image contents, source notices, model licenses, checksums, code/model pins and compatibility. Base images and model/package inputs are pinned; Debian apt packages and image timestamps are not bit-reproducible. GitHub Action major tags follow the source project's convention and are not immutable action commit pins.

## Publication

`images.yml` waits for the reusable verification workflow before publication. Main builds receive `edge`/commit tags; tagged releases receive SemVer/commit tags. Images go to `ghcr.io/normly/document-index-builder/{builder,retrieval}` with BuildKit provenance/SBOM and cosign keyless signatures bound to **this repository's** workflow, never the old `web-app` identity. Source/model preparation and synthetic CI are allowed on GitHub; no STACKIT operation/deployment credentials are configured there.

Verify with the expected workflow identity and OIDC issuer, for example:

```sh
cosign verify \
  --certificate-identity-regexp '^https://github\.com/normly/document-index-builder/\.github/workflows/images\.yml@refs/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  ghcr.io/normly/document-index-builder/retrieval@sha256:VERIFIED_DIGEST
```

Do not use an unverified registry tag as a production trust anchor. The implemented workflow has not been published or executed merely by adding it to this branch; actual registry permissions, release signatures and release assets require an authorized run.

## Knowledge releases and compatibility

Actual knowledge remains separately signed and calendar-versioned in STACKIT Object Storage. Software CI does not publish it. A knowledge release is promotable only after rights/export review, immutable-version checks, signature/part verification, recorded builder identity and retrieval acceptance. Unsigned `build-provenance.json` is informational, never a trust anchor.

Initial supported combination:

| Software | HTTP | Exchange | Database head | Query/index model |
|---|---|---|---|---|
| 0.1.0 | `/v1` (schema info 1.0.0) | 1 | `0002_build_identity` | multilingual-e5-large, revision `3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3`, 1024 dimensions |

`core/src/normly_core/model_artifacts.py` owns model pins; preparation and inspection reports reuse them. A model/strategy experiment uses isolated build storage and a compatible runtime, not an arbitrary model-ID change in a running instance. Runtime readiness and import checks enforce the supported combination. Follow the separately approved `web_app` cutover plan before deleting its old knowledge code or changing user-data references.
