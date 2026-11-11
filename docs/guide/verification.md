# Extraction verification record

This is a local synthetic verification record, not a production deployment or
registry publication. The extraction source is `web-app-local_dev_tooling` at
`41a3ce276505f2edd11bdb5ad0db1ae85acbed64`; its unrelated untracked
`.github/dependabot.yml` was preserved. `web_app` product code and live databases
were not modified.

## Evidence

- Ran all 43 legacy migrations in disposable PostgreSQL/pgvector and compared
  the 14 extracted baseline tables with the new baseline: column types/defaults,
  checks, unique constraints, foreign keys and indexes matched. Preserved six
  migration-only server defaults and `segment.text`'s SQL `TEXT` type that the
  old ORM did not fully describe. New build identity is a separate migration.
- Generated an export using the **original** exporter and synthetic rows,
  verified it using the extracted verifier, and imported it into a fresh
  knowledge-only database with the same document UUID.
- Ran the complete package/developer/lifecycle suite with cached pinned e5 and
  Docling models, offline: **509 passed**. The three image-only cases are
  deliberately opt-in in the ordinary suite and were run separately:
  **3 passed**. The suite reports upstream Starlette/AnyIO and Docling/Pydantic
  deprecation warnings; they were not hidden as successful real-source checks.
- Built both runtime images locally and inspected actual contents: non-root,
  prepared offline weights, full license text, no source PDFs/private inputs,
  and no importable Docling in retrieval.
- Ran `tests/container_smoke.py`: single-PDF container inspection with four
  output files and host ownership; two isolated build configurations producing
  signed releases; fresh consumer import and ready API; document search and
  three parsed segments; explicit update; rejected bad signature preserving
  the active release; restart preservation. Only the rehearsal's newly created
  unique Docker projects/volumes were removed.
- OpenAPI equality and intentional-schema-drift rejection passed. Compared
  the original `/v1` operations and components with the extracted schema;
  `/v1` remains unchanged. License metadata is corrected to AGPL, and readiness
  is an additive route with an explicitly modeled 503 response.
- Bash syntax and workflow YAML parsing passed. The release bake definition
  resolves both repository-specific registry namespaces and provenance/SBOM
  attestations without publishing.

See [releasing](releasing.md) for repeatable commands and
[`tests/container_smoke.py`](../../tests/container_smoke.py) for the container
rehearsal. Use prepared models, not implicit runtime downloads. Final branch
review and any subsequent fix verification are recorded in Git history.

## Deliberate boundaries and outstanding external checks

- No real/private corpus or publisher canary was accessed. Synthetic Docling
  and embedding checks validate wiring, not comprehensive extraction/retrieval
  quality for production sources.
- The VS Code task definitions and their exact terminal wrappers were tested;
  the graphical editor/Markdown preview was not exercised in this headless
  session.
- GitHub workflows were authored and checked locally, not pushed/executed.
  Actual registry publication, OIDC signatures, SBOM/provenance uploads and
  release assets still require an authorized CI run.
- User-data migrations, new passage/batch/notification contracts and production
  rollback remain gated by the separate `web_app` cutover design. Fresh isolated
  experimental databases do not promise identical UUIDs across rebuilds;
  export/import preserves a build's identifiers and retains missing IDs as
  tombstones.
- Knowledge signing keys used by tests were ephemeral and synthetic. No real
  signing ceremony, corpus publication, production key management or encrypted
  infrastructure setup was performed by this change.
