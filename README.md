# document-index-builder

Build searchable knowledge from authorized source PDFs, then serve it through a
separate retrieval API.

## Architecture at a glance

- **Source documents:** The project corpus is maintained in the private
  [`normly/web-app-raw-data`](https://github.com/normly/web-app-raw-data)
  repository and pinned here as the `web-app-raw-data` submodule. The corpus is
  input data; it is not part of this repository's software images.
- **Build:** The Builder OCI image from this repository processes authorized
  PDFs and writes relational knowledge and 1024-dimensional vectors to its
  dedicated PostgreSQL/pgvector build database. It exports an immutable signed
  Parquet release—not a PostgreSQL dump or database image.
- **Retrieval:** A separate Retrieval OCI image from this repository verifies
  and imports that release into its own PostgreSQL/pgvector consumer database,
  then serves the versioned HTTP API.
- **Application boundary:** `web_app` owns accounts, chat and user state. It
  consumes retrieval over private HTTP; it does not connect directly to the
  knowledge database.

The [architecture guide](docs/architecture.md) has the component views, artifact
formats, source provenance, runtime data flow and HTTP API documentation.

Only process registered sources with the applicable rights classification.
Public CI uses synthetic inputs only. Operational data and publication belong
on authorized STACKIT infrastructure. Never commit PDFs, extracted text,
knowledge releases or secrets.

## Workflow guides

Use the workflow skill as the canonical source for task commands and procedures.
The linked guides provide supporting technical and policy detail; this README
intentionally contains no executable command examples.

| Workflow | Skill | Guide |
|---|---|---|
| Build or rebuild the Builder or Retrieval image | [building-document-index-images](.agents/skills/building-document-index-images/SKILL.md) | [Independent software releases](docs/guide/releasing.md) |
| Inspect one PDF or tune extraction | [inspecting-document-index-pdfs](.agents/skills/inspecting-document-index-pdfs/SKILL.md) | [Inspecting PDFs](docs/guide/inspecting-pdfs.md) |
| Build a signed knowledge release | [building-document-index-releases](.agents/skills/building-document-index-releases/SKILL.md) | [Building knowledge](docs/guide/building-knowledge.md), [signed releases](docs/guide/knowledge-releases.md) |
| Run retrieval, import/update knowledge or check readiness | [running-document-index-retrieval](.agents/skills/running-document-index-retrieval/SKILL.md) | [Self-hosting](docs/guide/self-hosting.md), [retrieval API](docs/guide/retrieval-api.md) |
| Verify adapters or perform local real-PDF acceptance | — | [Verification guide](docs/guide/verification.md) |

For software development and review, see [CONTRIBUTING.md](CONTRIBUTING.md),
[REVIEW.md](REVIEW.md) and the [verification guide](docs/guide/verification.md).
Repository-wide safety and engineering rules are in [AGENTS.md](AGENTS.md).

## License

The software source code in this repository is licensed under the GNU Affero
General Public License v3.0 (AGPL-3.0). See [`LICENSE`](LICENSE). Source
documents and generated data may have separate rights and terms.
