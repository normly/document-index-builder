# document_index

Ingestion and document index generation.

This repository owns the knowledge-base builder, signed Parquet releases and
stable retrieval API. `web_app` remains the consumer application; it does not
run ingestion or access knowledge tables directly.

## Workflows

- [Inspect one PDF in VS Code or the terminal](docs/guide/inspecting-pdfs.md)
- [Build an isolated knowledge release](docs/guide/building-knowledge.md)
- [Run a populated retrieval service](docs/guide/self-hosting.md)
- [HTTP contract and semantics](docs/guide/retrieval-api.md) / [OpenAPI](api/openapi.yaml)
- [Signed knowledge exchange](docs/guide/knowledge-releases.md)
- [Software verification and releases](docs/guide/releasing.md)
- [Extraction ownership and coordinated web_app cutover](docs/guide/extraction-map.md)

Docker builds have two targets: `builder` (ingestion and single-PDF inspection)
and `retrieval` (query API, without Docling). PostgreSQL is separate; neither
image contains source PDFs or a populated knowledge database. Consumers import
a separately signed knowledge release on first start.

## License

The software source code in this repository is licensed under the GNU Affero
General Public License v3.0 (AGPL-3.0). See [`LICENSE`](LICENSE). Source
documents and generated data may have separate rights and terms.
