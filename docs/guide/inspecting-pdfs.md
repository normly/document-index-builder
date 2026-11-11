# Inspect one PDF locally

Use the **builder image**, not the retrieval image. Inspection parses one explicitly authorized PDF and writes Markdown/native Docling JSON without starting PostgreSQL, computing embeddings, chunking or publishing anything. Linux, Bash, GNU coreutils and Docker Compose/buildx are the local prerequisites; no host Python environment is required.

## First use

1. Run **Terminal → Run Task → Document Index: Build builder image** in VS Code. Image preparation downloads pinned code/model artifacts; subsequent parsing is offline.
2. Copy `configs/docling.example.json` to `.local/inspection-config.json`. Compute the authorized PDF's hash with `sha256sum -- '/path/with spaces/example.pdf'` and enter its hexadecimal digest as `input_sha256`.
3. Select its registered source (`baua`, `dguv`, `eur-lex`), source jurisdiction and documented processing classification. Set `may_process` to true only when that classification actually permits processing. Missing permission, wrong source or a different PDF hash is refused. Choosing an adapter does not grant rights.
4. Run **Document Index: Inspect PDF**, supplying the PDF path, local configuration, source and a fresh output directory. The default is `.local/inspection/example`. Do not reuse a previous output directory implicitly; choose `example-02` for another experiment.
5. Open `document.md`, then **Markdown: Open Preview to the Side**. Open `document.json` to investigate structure lost in Markdown. Compare `configuration.json` and `report.json` between experiments.

Equivalent terminal commands:

```sh
docker buildx bake -f docker-bake.hcl --load builder
scripts/inspect-pdf '/path/with spaces/example.pdf' \
  .local/inspection-config.json baua .local/inspection/example
```

Inputs and configuration are mounted read-only. Only a private temporary output directory is writable, rather than exposing its whole parent to the parser. The container uses the host UID/GID and a temporary cache, so outputs are not root-owned. Failures preserve exit codes, existing destinations remain untouched, and temporary outputs are cleaned. Paths containing spaces are supported; colons in bind-mount paths are rejected explicitly. Inspection needs no database password even though full builds use the same Compose file.

## Configuration and output

Supported initial settings: `do_table_structure` (boolean), `table_structure_mode` (`fast` or `accurate`) and `accelerator_threads` (1–64). CPU is the only supported accelerator. OCR remains disabled because the prepared image does not include OCR models; enabling it would introduce unpinned runtime downloads. Unknown/unsupported values fail instead of silently falling back.

Both production ingestion and inspection use the same `docling_config.py` parser and converter configuration. Copy the inspection configuration's `docling` object into the build configuration's optional `docling` field when promoting an experiment. Converter caching includes all settings, so one experiment cannot accidentally reuse another's converter.

Outputs are `document.md`, native `document.json`, effective `configuration.json`, and `report.json` (input digest, versions, expected pinned model revisions, elapsed time and warnings). The model revisions describe the pinned image; custom artifact directories require separate operator verification. Extraction is strict: partial Docling conversion is an error, not a successful Markdown export. Warnings from underlying libraries also remain visible in task output.

These outputs contain source text. `.local/` is excluded from Git and the Docker context; keep it on permitted local storage and never attach outputs to public issues or CI artifacts. Delete only the specific experiment directories you intend to remove. No custom UI, batch PDF runner or configuration-comparison framework is provided in this initial tool.
