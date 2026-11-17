# document-index-builder

Turn authorized source documents into a searchable knowledge base. Start small by converting single PDFs per standard family to Markdown so you can check how headings, text and tables are extracted. For repeatable adapter checks, keep manually reviewed expectations in `web-app-raw-data/raw_data_test/<family>/extraction-test-annotations.json`, using the shared template and instructions in that private submodule. One family-neutral local test harness discovers those files and selects the registered adapter named by each case.

When extraction settings work, build a signed knowledge release from pinned
builder software and source inputs. The builder stores parsed knowledge in its
dedicated PostgreSQL/pgvector build database, then exports the release—not a
database dump. The release contains Parquet files for approved knowledge tables,
plus a manifest and signature. On deployment, retrieval verifies and imports the
release into its own, separate PostgreSQL/pgvector database; that is the database
the API serves from. Build-only state is not included in the release.

The **Builder** image ingests documents and creates releases. The **Retrieval**
image serves the search API from the separately populated consumer database.

Not part of the scope of this repo: `web_app` owns accounts, chat and user state; it communicates with retrieval over HTTP.

## Start here: inspect one PDF

### What you need

- Linux with Docker Engine, Docker Compose and Docker buildx available.
- A PDF you are permitted to process, on an approved storage location.
- VS Code if you want the editor tasks and Markdown preview (optional).

You do **not** need Python installed on your machine, a database or a signing
key to inspect a PDF. The first image build downloads software and pinned model
weights; subsequent parsing runs offline. Allow time and disk space for that
initial build.

Run the following from the repository root.

### 1. Build the builder image

```sh
REGISTRY= PUSH=0 docker buildx bake -f docker-bake.hcl --load builder
```

This prepares the local software image. It does not process documents or start
a database.

### 2. Prepare the PDF's inspection settings

```sh
mkdir -p .local
cp -n configs/docling.example.json .local/inspection-config.json
sha256sum -- '/path/with spaces/example.pdf'
```

Replace the example PDF path with your own. Open `.local/inspection-config.json`
and set:

- `input_sha256` to the hash printed by `sha256sum`.
- `source` to the matching registered source: `baua`, `dguv` or `eur-lex`.
- `rights` to the documented jurisdiction and legal basis permitting this PDF
  to be processed. The example deliberately sets `may_process` to `false`;
  change it only if that classification permits processing.

Choosing a source does not grant permission. If your PDF has no applicable
registration or rights classification, stop rather than bypassing the checks.
Existing local configuration is preserved by the copy command.

### 3. Inspect and open the result

For a BAuA PDF, with `source` set to `baua` in the configuration:

```sh
bash scripts/inspect-pdf '/path/with spaces/example.pdf' \
  .local/inspection-config.json baua .local/inspection/example-01
```

Use the matching source name for other registered sources. Choose a **new output
directory** for each experiment; do not reuse or create it while inspection runs.

The output contains:

| File | What it is for |
|---|---|
| `document.md` | Read the extracted content and preview it as Markdown. |
| `document.json` | Inspect Docling's structured document representation. |
| `configuration.json` | See the effective settings used for this run. |
| `report.json` | Check versions, input hash, elapsed time and warnings. |

In VS Code, open `document.md` and select **Markdown: Open Preview to the Side**.
See the [PDF inspection guide](docs/guide/inspecting-pdfs.md) for supported parser
settings and troubleshooting.

### Prefer VS Code tasks?

Use **Terminal → Run Task**:

| Task | When to use it |
|---|---|
| **Document Index: Build builder image** | Prepare or rebuild the builder. |
| **Document Index: Inspect PDF** | Supply a PDF, configuration, source and fresh output path. |
| **Document Index: Build knowledge release** | Build a complete release after preparing authorized inputs, configuration, dedicated build storage and a signing key. |

## Validate adapters

The private `web-app-raw-data` submodule contains the JSON template, per-family
annotation records, and the detailed [real-PDF test guide](web-app-raw-data/EXTRACTION_TESTS.md).
The generic test harness checks selected Docling properties and the adapter's
annotated records, sections, and anchor assignments. It is local-only and
requires human-verified annotations; ordinary CI remains synthetic-only. After
reviewing a case and preparing pinned Docling artifacts offline, run from the
repository root:

```sh
RUN_REAL_PDF_TESTS=1 uv run --group dev --all-packages --all-extras \
  python -m pytest \
  core/tests/pipeline/test_real_pdf_annotations.py \
  core/tests/pipeline/test_real_pdf_extraction.py -q
```

Draft annotations fail the opt-in validation guard; tests skip private inputs
when the environment variable is unset.

## Next steps

- **Build a knowledge release:** follow [Building knowledge](docs/guide/building-knowledge.md).
  Unlike PDF inspection, this needs a dedicated database and a signing key.
- **Run search over prepared knowledge:** follow [Self-hosting](docs/guide/self-hosting.md).
  Retrieval imports a separately trusted, signed release; it does not ingest PDFs.
- **Develop or test the software:** read [CONTRIBUTING.md](CONTRIBUTING.md),
  [REVIEW.md](REVIEW.md) and [verification and releases](docs/guide/releasing.md).

### Where source documents live

The source corpus is maintained in the private
[`web-app-raw-data` repository](https://github.com/normly/web-app-raw-data),
pinned here as the `web-app-raw-data` submodule. Initialize it after cloning with
`git submodule update --init web-app-raw-data` (or clone with
`--recurse-submodules`). For an authorized local build, pass the relevant source
directory to `scripts/build-knowledge`, which mounts it read-only at `/inputs`.
The corpus is intentionally excluded from this repository's Docker build context
and CI; its presence as a submodule does not authorize processing or publishing.

Only process sources you are authorized to use. Extracted text and JSON contain
source content: keep them on permitted storage, normally in ignored `.local/`
directories, and never commit them or upload them to public issues or CI.
Operational data and publication belong on STACKIT; the limited local-testing
exception is not permission to process arbitrary sources. See [AGENTS.md](AGENTS.md)
for the repository's safety and rights rules.

## For AI coding assistants

Repository skills are task-specific instructions, not a prerequisite for humans
following the quick start above. Read the matching `SKILL.md` before performing
a workflow:

| Task | Skill |
|---|---|
| Build Docker images | [building-document-index-images](.agents/skills/building-document-index-images/SKILL.md) |
| Inspect a PDF or tune parsing | [inspecting-document-index-pdfs](.agents/skills/inspecting-document-index-pdfs/SKILL.md) |
| Build a signed knowledge release | [building-document-index-releases](.agents/skills/building-document-index-releases/SKILL.md) |
| Run retrieval, update knowledge or verify locally | [running-document-index-retrieval](.agents/skills/running-document-index-retrieval/SKILL.md) |

[AGENTS.md](AGENTS.md) provides task routing and mandatory constraints. If an
assistant does not discover `.agents/skills/` automatically, open the linked
file directly; no global skill installation is required.

## Reference

- [Retrieval API semantics](docs/guide/retrieval-api.md) / [OpenAPI](api/openapi.yaml)
- [Signed knowledge exchange](docs/guide/knowledge-releases.md)
- [Extraction ownership and coordinated web_app cutover](docs/guide/extraction-map.md)
- [Verification evidence and remaining external checks](docs/guide/verification.md)

## License

The software source code in this repository is licensed under the GNU Affero
General Public License v3.0 (AGPL-3.0). See [`LICENSE`](LICENSE). Source
documents and generated data may have separate rights and terms.
